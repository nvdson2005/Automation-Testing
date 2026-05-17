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


class FT005Test(unittest.TestCase):
    """Level 2: URLs and selectors loaded from FT005_config.csv."""

    _DIR = os.path.dirname(__file__)
    _CSV = os.path.join(_DIR, "FT005_data.csv")
    _CFG = os.path.join(_DIR, "FT005_config.csv")

    @classmethod
    def setUpClass(cls):
        cls.cfg = _load_config(cls._CFG)

    # ── helpers ────────────────────────────────────────────────────────────

    def _make_driver(self):
        driver = webdriver.Chrome()
        driver.implicitly_wait(int(self.cfg.get("implicit_wait", "30")))
        return driver

    def _login_as_student(self, driver):
        driver.get(self.cfg["base_url"])
        driver.implicitly_wait(0)
        login_needed = self._is_element_present(driver, By.LINK_TEXT, self.cfg["login_link_text"])
        driver.implicitly_wait(int(self.cfg.get("implicit_wait", "30")))
        if login_needed:
            driver.find_element(By.LINK_TEXT, self.cfg["login_link_text"]).click()
            driver.find_element(By.ID, self.cfg["username_field_id"]).clear()
            driver.find_element(By.ID, self.cfg["username_field_id"]).send_keys(self.cfg["student_username"])
            driver.find_element(By.ID, self.cfg["password_field_id"]).clear()
            driver.find_element(By.ID, self.cfg["password_field_id"]).send_keys(self.cfg["student_password"])
            driver.find_element(By.ID, self.cfg["login_form_id"]).submit()
        driver.get(self.cfg["courses_url"])

    def _open_course(self, driver, course_id: str):
        """Navigate to a course page using externalized URL template."""
        course_url = self.cfg["course_url_template"] + course_id
        driver.get(course_url)
        WebDriverWait(driver, int(self.cfg.get("wait_timeout", "15"))).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

    def _get_completion_status(self, driver) -> str:
        """Extract course completion status using externalized selectors."""
        try:
            driver.implicitly_wait(0)
            completion_xpath = self.cfg["completion_status_xpath"]

            driver.implicitly_wait(int(self.cfg.get("implicit_wait", "30")))
            try:
                elem = driver.find_element(By.XPATH, completion_xpath)
                if elem.is_displayed():
                    return self.cfg["completion_text_completed"]
            except NoSuchElementException:
                pass

            driver.implicitly_wait(0)
            driver.implicitly_wait(int(self.cfg.get("implicit_wait", "30")))
            return self.cfg["completion_text_not_completed"]

        except Exception:
            driver.implicitly_wait(int(self.cfg.get("implicit_wait", "30")))
            return self.cfg.get("completion_text_no_status", "No Status")

    def _is_element_present(self, driver, how, what):
        try:
            driver.find_element(by=how, value=what)
        except NoSuchElementException:
            return False
        return True

    # ── test ───────────────────────────────────────────────────────────────

    def test_course_completion_status(self):
        with open(self._CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                with self.subTest(test_id=row["test_id"]):
                    verification_errors = []
                    driver = self._make_driver()
                    try:
                        self._login_as_student(driver)
                        self._open_course(driver, row["course_id"])
                        time.sleep(int(self.cfg.get("page_load_wait", "2")))

                        actual_status = self._get_completion_status(driver)
                        expected_status = row["expected"]

                        try:
                            self.assertEqual(
                                expected_status,
                                actual_status,
                                f"Expected status: {expected_status}, Got: {actual_status}"
                            )
                        except AssertionError as e:
                            verification_errors.append(str(e))

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
