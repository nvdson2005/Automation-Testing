# -*- coding: utf-8 -*-
import csv
import os
import unittest

from selenium import webdriver
from selenium.common.exceptions import (
    ElementNotInteractableException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


USERNAME = "williamkim"
BASE_URL = "https://school.moodledemo.net"
LOGIN_URL = f"{BASE_URL}/login/index.php"
CHANGE_PASSWORD_URL = f"{BASE_URL}/login/change_password.php?id=1"
BASELINE_PASSWORD = os.getenv("FT003_BASELINE_PASSWORD", "mood" + "le")

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(ROOT_DIR, "FT003_data.csv")


class FT003ChangePasswordDataDrivenTest(unittest.TestCase):
    driver = None
    current_password = None
    rows = []
    known_passwords = []

    @classmethod
    def setUpClass(cls):
        cls.rows = cls._load_rows()
        cls.known_passwords = cls._collect_known_passwords(cls.rows)
        cls.driver = webdriver.Chrome()
        cls.driver.implicitly_wait(1)
        cls._normalize_password(BASELINE_PASSWORD)

    @classmethod
    def tearDownClass(cls):
        try:
            if cls.driver is not None:
                cls._normalize_password(BASELINE_PASSWORD)
        finally:
            if cls.driver is not None:
                cls.driver.quit()

    @staticmethod
    def _load_rows():
        with open(DATA_FILE, newline="", encoding="utf-8-sig") as csv_file:
            return list(csv.DictReader(csv_file))

    @classmethod
    def _collect_known_passwords(cls, rows):
        fields = (
            "login_password",
            "current_password",
            "new_password1",
            "new_password2",
            "password_after_test",
        )
        passwords = [BASELINE_PASSWORD]
        for row in rows:
            for field in fields:
                value = row.get(field, "").strip()
                if value and value not in passwords:
                    passwords.append(value)
        return passwords

    @staticmethod
    def _wait(driver, seconds=10):
        return WebDriverWait(driver, seconds)

    @classmethod
    def _find_first(cls, locators, seconds=5):
        last_error = None
        for locator in locators:
            try:
                return cls._wait(cls.driver, seconds).until(
                    EC.presence_of_element_located(locator)
                )
            except TimeoutException as exc:
                last_error = exc
        raise last_error

    @staticmethod
    def _set_text(element, value):
        element.clear()
        element.send_keys(value)

    @classmethod
    def _reset_browser(cls):
        cls.driver.delete_all_cookies()

    @classmethod
    def _dismiss_continue(cls):
        buttons = cls.driver.find_elements(
            By.XPATH,
            "//button[normalize-space()='Continue'] | //a[normalize-space()='Continue']",
        )
        for button in buttons:
            try:
                if button.is_displayed() and button.is_enabled():
                    button.click()
                    return
            except (ElementNotInteractableException, StaleElementReferenceException):
                continue

    @classmethod
    def _login(cls, password):
        cls._reset_browser()
        cls.driver.get(LOGIN_URL)
        cls._dismiss_continue()

        username = cls._wait(cls.driver).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        cls._set_text(username, USERNAME)

        password_input = cls._find_first([(By.ID, "password"), (By.ID, "passwordinput")])
        cls._set_text(password_input, password)

        login_buttons = cls.driver.find_elements(By.ID, "loginbtn")
        if login_buttons:
            login_buttons[0].click()
        else:
            cls.driver.find_element(By.ID, "login").submit()

        try:
            cls._wait(cls.driver, 8).until(
                lambda driver: driver.find_elements(By.ID, "user-menu-toggle")
                or driver.find_elements(By.CSS_SELECTOR, "body.pagelayout-mycourses")
                or driver.find_elements(By.ID, "loginerrormessage")
            )
        except TimeoutException:
            return "/login/" not in cls.driver.current_url

        return not cls.driver.find_elements(By.ID, "loginerrormessage")

    @classmethod
    def _open_change_password_page(cls):
        cls.driver.get(CHANGE_PASSWORD_URL)
        cls._dismiss_continue()
        cls._wait(cls.driver).until(
            EC.presence_of_element_located((By.ID, "id_submitbutton"))
        )

    @classmethod
    def _fill_change_password_form(cls, row):
        field_map = {
            "current_password": "id_password",
            "new_password1": "id_newpassword1",
            "new_password2": "id_newpassword2",
        }
        for csv_field, element_id in field_map.items():
            value = row.get(csv_field, "")
            if value:
                cls._set_text(cls.driver.find_element(By.ID, element_id), value)

    @classmethod
    def _submit_or_cancel(cls, action):
        button_id = "id_cancel" if action == "cancel" else "id_submitbutton"
        cls.driver.find_element(By.ID, button_id).click()

    @classmethod
    def _change_password_directly(cls, old_password, new_password):
        if not cls._login(old_password):
            return False

        cls._open_change_password_page()
        cls._set_text(cls.driver.find_element(By.ID, "id_password"), old_password)
        cls._set_text(cls.driver.find_element(By.ID, "id_newpassword1"), new_password)
        cls._set_text(cls.driver.find_element(By.ID, "id_newpassword2"), new_password)
        cls.driver.find_element(By.ID, "id_submitbutton").click()
        cls._wait(cls.driver).until(
            EC.text_to_be_present_in_element((By.ID, "notice"), "Password has been changed")
        )
        cls.current_password = new_password
        return True

    @classmethod
    def _normalize_password(cls, target_password):
        if not target_password:
            return

        if cls.current_password == target_password and cls._login(target_password):
            return

        if cls._login(target_password):
            cls.current_password = target_password
            return

        for candidate in cls.known_passwords:
            if candidate and candidate != target_password:
                if cls._change_password_directly(candidate, target_password):
                    return

        raise AssertionError(
            f"Could not normalize account password to {target_password!r}. "
            "Update FT003_data.csv with the current live password if it changed outside this suite."
        )

    def test_ft003_change_password_from_csv(self):
        for row in self.rows:
            test_id = row["test_id"].strip()
            with self.subTest(test_id=test_id, source=row["source_file"]):
                if row["expect_type"] == "manual_review":
                    self.skipTest(row["notes"])
                self._run_csv_case(row)

    def _run_csv_case(self, row):
        start_password = row["login_password"].strip() or self.current_password
        self.__class__._normalize_password(start_password)

        self.assertTrue(
            self._login(start_password),
            f"Login failed with starting password for {row['test_id']}",
        )

        self._open_change_password_page()
        self._fill_change_password_form(row)
        if row["expect_type"].strip() == "success_truncated_password":
            self._assert_truncated_password_inputs(row)
        self._submit_or_cancel(row["action"].strip())
        self._assert_expected_result(row)

        expected_state = row["password_after_test"].strip() or start_password
        self.__class__.current_password = expected_state

    def _assert_expected_result(self, row):
        expect_type = row["expect_type"].strip()

        if expect_type == "success_notice":
            self._assert_element_contains(row["assert_element_id"], row["expected_text"])
            expected_password = row["password_after_test"].strip()
            self.assertEqual("1", row["mutates_password"].strip())
            self.assertTrue(
                self._login(expected_password),
                f"Expected login to succeed with password for {row['test_id']}",
            )
            return

        if expect_type == "success_truncated_password":
            self._assert_element_contains(row["assert_element_id"], row["expected_text"])
            attempted_password = row["new_password1"].strip()
            stored_password = row["password_after_test"].strip()
            self.assertEqual("1", row["mutates_password"].strip())
            self.assertFalse(
                self._login(attempted_password),
                f"Expected login with untruncated password to fail for {row['test_id']}",
            )
            self.assertTrue(
                self._login(stored_password),
                f"Expected login with truncated password to succeed for {row['test_id']}",
            )
            return

        if expect_type == "error":
            self._assert_element_contains(row["assert_element_id"], row["expected_text"])
            self.assertEqual("0", row["mutates_password"].strip())
            return

        if expect_type == "error_multi":
            element_ids = row["assert_element_id"].split("|")
            expected_texts = row["expected_text"].split("|")
            self.assertEqual(
                len(element_ids),
                len(expected_texts),
                "CSV multi-error fields must have matching lengths",
            )
            for element_id, expected_text in zip(element_ids, expected_texts):
                self._assert_element_contains(element_id, expected_text)
            self.assertEqual("0", row["mutates_password"].strip())
            return

        if expect_type == "password_unchanged":
            self.assertEqual("0", row["mutates_password"].strip())
            self.assertTrue(
                self._login(row["expected_text"].strip()),
                f"Expected password to remain unchanged for {row['test_id']}",
            )
            return

        self.fail(f"Unsupported expect_type: {expect_type}")

    def _assert_truncated_password_inputs(self, row):
        expected_value = row["password_after_test"].strip()
        attempted_value = row["new_password1"].strip()
        self.assertLess(len(expected_value), len(attempted_value))
        for element_id in ("id_newpassword1", "id_newpassword2"):
            actual_value = self.driver.find_element(By.ID, element_id).get_attribute("value")
            self.assertEqual(expected_value, actual_value)

    def _assert_element_contains(self, element_id, expected_text):
        actual_text = self._wait(self.driver).until(
            EC.presence_of_element_located((By.ID, element_id.strip()))
        ).text
        self.assertIn(expected_text.strip(), actual_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
