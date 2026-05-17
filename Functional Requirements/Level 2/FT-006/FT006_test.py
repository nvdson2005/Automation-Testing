# -*- coding: utf-8 -*-
import csv
import os
import time
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException


def _load_config(path):
    with open(path, newline="", encoding="utf-8") as f:
        return {row["key"]: row["value"] for row in csv.DictReader(f)}


class FT006Test(unittest.TestCase):
    """Level 2: URLs and selectors loaded from FT006_config.csv."""

    _DIR = os.path.dirname(__file__)
    _CSV = os.path.join(_DIR, "FT006_data.csv")
    _CFG = os.path.join(_DIR, "FT006_config.csv")

    @classmethod
    def setUpClass(cls):
        cls.cfg = _load_config(cls._CFG)

    # ── helpers ────────────────────────────────────────────────────────────

    def _make_driver(self):
        driver = webdriver.Chrome()
        driver.implicitly_wait(int(self.cfg.get("implicit_wait", "30")))
        return driver

    def _login(self, driver, username: str, password: str):
        driver.get(self.cfg["base_url"])
        driver.implicitly_wait(0)
        login_needed = self._is_element_present(driver, By.LINK_TEXT, self.cfg["login_link_text"])
        driver.implicitly_wait(int(self.cfg.get("implicit_wait", "30")))
        if login_needed:
            driver.find_element(By.LINK_TEXT, self.cfg["login_link_text"]).click()
            driver.find_element(By.ID, self.cfg["username_field_id"]).clear()
            driver.find_element(By.ID, self.cfg["username_field_id"]).send_keys(username)
            driver.find_element(By.ID, self.cfg["password_field_id"]).clear()
            driver.find_element(By.ID, self.cfg["password_field_id"]).send_keys(password)
            driver.find_element(By.ID, self.cfg["login_form_id"]).submit()
        WebDriverWait(driver, int(self.cfg.get("wait_timeout", "30"))).until(EC.url_contains("moodledemo.net"))

    def _navigate_to_edit_profile(self, driver):
        """Navigate to profile edit page using externalized URLs."""
        profile_url = self.cfg["profile_url"]
        driver.get(profile_url)
        WebDriverWait(driver, int(self.cfg.get("wait_timeout", "15"))).until(
            EC.presence_of_element_located((By.ID, self.cfg["first_name_field_id"]))
        )

    def _scroll_to_picture_section(self, driver):
        """Scroll to user picture section using externalized selector."""
        driver.execute_script(f"""
            var elem = document.querySelector('{self.cfg["picture_section_selector"]}');
            if (elem) elem.scrollIntoView(true);
        """)
        time.sleep(1)

    def _upload_file(self, driver, file_path: str):
        """Upload a file to user picture input using externalized selector."""
        if not file_path or file_path.lower() == "none":
            return False
        try:
            file_input = driver.find_element(By.XPATH, self.cfg["file_input_xpath"])
            if os.path.exists(file_path):
                file_input.send_keys(os.path.abspath(file_path))
                time.sleep(1)
                return True
            else:
                print(f"File not found: {file_path}")
                return False
        except NoSuchElementException:
            print("File input element not found")
            return False

    def _set_description(self, driver, description: str):
        """Set picture description using externalized selector."""
        if not description or description.lower() == "none":
            return
        try:
            desc_field = driver.find_element(By.ID, self.cfg["description_field_id"])
            if desc_field:
                desc_field.clear()
                desc_field.send_keys(description)
        except NoSuchElementException:
            pass

    def _get_error_message(self, driver) -> str:
        """Get error message from page using externalized selectors."""
        try:
            error_elem = driver.find_element(By.XPATH, self.cfg["error_message_xpath"])
            return error_elem.text
        except NoSuchElementException:
            return ""

    def _get_success_message(self, driver) -> str:
        """Get success message from page using externalized selector."""
        try:
            success_elem = driver.find_element(By.XPATH, self.cfg["success_message_xpath"])
            return success_elem.text
        except NoSuchElementException:
            return ""

    def _is_element_present(self, driver, how, what):
        try:
            driver.find_element(by=how, value=what)
        except NoSuchElementException:
            return False
        return True

    # ── test ───────────────────────────────────────────────────────────────

    def test_user_picture_upload(self):
        with open(self._CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                with self.subTest(test_id=row["test_id"]):
                    verification_errors = []
                    driver = self._make_driver()
                    try:
                        self._login(driver, row["username"], row["password"])
                        self._navigate_to_edit_profile(driver)
                        self._scroll_to_picture_section(driver)

                        if row.get("file_path") and row["file_path"].lower() != "none":
                            self._upload_file(driver, row["file_path"])

                        if row.get("description") and row["description"].lower() != "none":
                            self._set_description(driver, row["description"])

                        if row.get("action") == "delete_picture":
                            try:
                                delete_checkbox = driver.find_element(By.ID, self.cfg["delete_picture_checkbox_id"])
                                delete_checkbox.click()
                            except NoSuchElementException:
                                pass

                        time.sleep(1)
                        driver.find_element(By.ID, self.cfg["submit_button_id"]).click()
                        time.sleep(2)

                        expected = row["expected"]
                        if expected == "success":
                            success_msg = self._get_success_message(driver)
                            body_text = driver.find_element(By.TAG_NAME, "body").text
                            if "changes" not in body_text.lower() and "updated" not in body_text.lower():
                                if not success_msg:
                                    verification_errors.append("Expected success but no confirmation found")
                        else:  # error expected
                            error_msg = self._get_error_message(driver)
                            if expected not in error_msg:
                                verification_errors.append(f"Expected error: {expected}, Got: {error_msg}")

                        self.assertEqual([], verification_errors)

                    except Exception as e:
                        driver.save_screenshot(f"fail_{row['test_id']}.png")
                        print(f"\n[FAIL {row['test_id']}] URL: {driver.current_url}")
                        print(f"[FAIL {row['test_id']}] Error: {str(e)}")
                        raise
                    finally:
                        driver.quit()


if __name__ == "__main__":
    unittest.main()
