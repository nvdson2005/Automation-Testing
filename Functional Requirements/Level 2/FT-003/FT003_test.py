# -*- coding: utf-8 -*-
import csv
import json
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


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(ROOT_DIR, "FT003_data.csv")
CONFIG_FILE = os.path.join(ROOT_DIR, "FT003_config.json")
ELEMENTS_FILE = os.path.join(ROOT_DIR, "FT003_elements.json")


class FT003Level2ChangePasswordTest(unittest.TestCase):
    driver = None
    config = {}
    elements = {}
    rows = []
    known_passwords = []
    current_password = None

    @classmethod
    def setUpClass(cls):
        cls.config = cls._load_json(CONFIG_FILE)
        cls.elements = cls._load_json(ELEMENTS_FILE)
        cls.rows = cls._load_rows()
        cls.known_passwords = cls._collect_known_passwords(cls.rows)
        cls.driver = webdriver.Chrome()
        cls.driver.implicitly_wait(1)
        cls._normalize_password(cls._baseline_password())

    @classmethod
    def tearDownClass(cls):
        try:
            if cls.driver is not None:
                cls._normalize_password(cls._baseline_password())
        finally:
            if cls.driver is not None:
                cls.driver.quit()

    @staticmethod
    def _load_json(path):
        with open(path, encoding="utf-8") as json_file:
            return json.load(json_file)

    @staticmethod
    def _load_rows():
        with open(DATA_FILE, newline="", encoding="utf-8-sig") as csv_file:
            return list(csv.DictReader(csv_file))

    @classmethod
    def _baseline_password(cls):
        credentials = cls.config["credentials"]
        return os.getenv(
            credentials["baseline_password_env"],
            credentials["baseline_password_default"],
        )

    @classmethod
    def _collect_known_passwords(cls, rows):
        fields = (
            "login_password",
            "current_password",
            "new_password1",
            "new_password2",
            "password_after_test",
        )
        passwords = []
        for row in rows:
            for field in fields:
                value = row.get(field, "").strip()
                if value and value not in passwords:
                    passwords.append(value)
        return passwords

    @classmethod
    def _wait(cls, seconds=None):
        timeout = seconds or cls.config["timeouts"]["default"]
        return WebDriverWait(cls.driver, timeout)

    @staticmethod
    def _by(selector_type):
        mapping = {
            "id": By.ID,
            "xpath": By.XPATH,
            "css": By.CSS_SELECTOR,
            "link": By.LINK_TEXT,
            "name": By.NAME,
        }
        return mapping[selector_type]

    @classmethod
    def _element_definitions(cls, item_name):
        definition = cls.elements[item_name]
        return definition if isinstance(definition, list) else [definition]

    @classmethod
    def _locator(cls, definition):
        return cls._by(definition["by"]), definition["value"]

    @classmethod
    def _find_item(cls, item_name, seconds=None):
        timeout = seconds or cls.config["timeouts"]["locator"]
        last_error = None
        for definition in cls._element_definitions(item_name):
            try:
                return cls._wait(timeout).until(
                    EC.presence_of_element_located(cls._locator(definition))
                )
            except TimeoutException as exc:
                last_error = exc
        raise last_error

    @classmethod
    def _find_items(cls, item_name):
        matches = []
        for definition in cls._element_definitions(item_name):
            matches.extend(cls.driver.find_elements(*cls._locator(definition)))
        return matches

    @classmethod
    def _has_any_item(cls, item_names):
        return any(cls._find_items(item_name) for item_name in item_names)

    @staticmethod
    def _set_text(element, value):
        element.clear()
        element.send_keys(value)

    @classmethod
    def _click_item(cls, item_name):
        element = cls._find_item(item_name)
        if element.tag_name.lower() == "form":
            element.submit()
        else:
            element.click()

    @classmethod
    def _reset_browser(cls):
        cls.driver.delete_all_cookies()

    @classmethod
    def _dismiss_continue(cls):
        for control in cls._find_items("continue_controls"):
            try:
                if control.is_displayed() and control.is_enabled():
                    control.click()
                    return
            except (ElementNotInteractableException, StaleElementReferenceException):
                continue

    @classmethod
    def _login(cls, password):
        cls._reset_browser()
        cls.driver.get(cls.config["urls"]["login"])
        cls._dismiss_continue()

        username = cls._find_item("username_input")
        cls._set_text(username, cls.config["credentials"]["username"])

        password_input = cls._find_item("login_password_input")
        cls._set_text(password_input, password)
        cls._click_item("login_button")

        try:
            cls._wait(cls.config["timeouts"]["login"]).until(
                lambda _: cls._has_any_item(cls.config["login_success_indicators"])
                or cls._has_any_item(cls.config["login_error_indicators"])
            )
        except TimeoutException:
            return cls.config["urls"]["login_failure_fragment"] not in cls.driver.current_url

        return not cls._has_any_item(cls.config["login_error_indicators"])

    @classmethod
    def _open_change_password_page(cls):
        cls.driver.get(cls.config["urls"]["change_password"])
        cls._dismiss_continue()
        cls._find_item(cls.config["action_targets"]["submit"])

    @classmethod
    def _fill_change_password_form(cls, row):
        for csv_field, item_name in cls.config["field_bindings"].items():
            value = row.get(csv_field, "")
            if value:
                cls._set_text(cls._find_item(item_name), value)

    @classmethod
    def _perform_action(cls, action):
        target_item = cls.config["action_targets"][action]
        cls._click_item(target_item)

    @classmethod
    def _change_password_directly(cls, old_password, new_password):
        if not cls._login(old_password):
            return False

        cls._open_change_password_page()
        cls._set_text(cls._find_item("current_password_input"), old_password)
        cls._set_text(cls._find_item("new_password1_input"), new_password)
        cls._set_text(cls._find_item("new_password2_input"), new_password)
        cls._click_item("submit_button")
        cls._wait().until(
            EC.text_to_be_present_in_element(
                cls._locator(cls._element_definitions("success_notice")[0]),
                cls.config["assertions"]["password_changed_text"],
            )
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
            "Update FT003_data.csv if the live password changed outside this suite."
        )

    def test_ft003_change_password_from_csv_and_json_items(self):
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
        self._perform_action(row["action"].strip())
        self._assert_expected_result(row)

        expected_state = row["password_after_test"].strip() or start_password
        self.__class__.current_password = expected_state

    def _assert_expected_result(self, row):
        expect_type = row["expect_type"].strip()

        if expect_type == "success_notice":
            self._assert_item_contains(row["assert_item"], row["expected_text"])
            self.assertEqual("1", row["mutates_password"].strip())
            self.assertTrue(
                self._login(row["password_after_test"].strip()),
                f"Expected login to succeed with new password for {row['test_id']}",
            )
            return

        if expect_type == "success_truncated_password":
            self._assert_item_contains(row["assert_item"], row["expected_text"])
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
            self._assert_item_contains(row["assert_item"], row["expected_text"])
            self.assertEqual("0", row["mutates_password"].strip())
            return

        if expect_type == "error_multi":
            item_names = row["assert_item"].split("|")
            expected_texts = row["expected_text"].split("|")
            self.assertEqual(
                len(item_names),
                len(expected_texts),
                "CSV multi-error fields must have matching lengths",
            )
            for item_name, expected_text in zip(item_names, expected_texts):
                self._assert_item_contains(item_name, expected_text)
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
        for item_name in ("new_password1_input", "new_password2_input"):
            actual_value = self._find_item(item_name).get_attribute("value")
            self.assertEqual(expected_value, actual_value)

    def _assert_item_contains(self, item_name, expected_text):
        actual_text = self._find_item(item_name.strip()).text
        self.assertIn(expected_text.strip(), actual_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
