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


class FT005Test(unittest.TestCase):
    """Data-driven course completion condition tests. Test data in FT005_data.csv."""

    _CSV = os.path.join(os.path.dirname(__file__), "FT005_data.csv")

    # ── helpers ────────────────────────────────────────────────────────────

    def _make_driver(self) -> webdriver.Chrome:
        driver = webdriver.Chrome()
        driver.implicitly_wait(30)
        return driver

    def _login_as_student(self, driver: webdriver.Chrome):
        driver.get("https://school.moodledemo.net/")
        driver.implicitly_wait(0)
        login_needed = self._is_element_present(driver, By.LINK_TEXT, "Log in")
        driver.implicitly_wait(30)
        if login_needed:
            driver.find_element(By.LINK_TEXT, "Log in").click()
            driver.find_element(By.ID, "username").clear()
            driver.find_element(By.ID, "username").send_keys("student")
            driver.find_element(By.ID, "password").clear()
            driver.find_element(By.ID, "password").send_keys("moodle26")
            driver.find_element(By.ID, "login").submit()
        driver.get("https://school.moodledemo.net/my/courses.php")

    def _open_course(self, driver: webdriver.Chrome, course_id: str):
        """Navigate to a course page."""
        course_url = f"https://school.moodledemo.net/course/view.php?id={course_id}"
        driver.get(course_url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

    def _get_completion_status(self, driver: webdriver.Chrome) -> str:
        """
        Extract course completion status from the page.
        Looks for completion indicator in the course header or progress section.
        Returns: "Completed", "Not Completed", or "No Status"
        """
        try:
            # Try to find completion status in course header
            driver.implicitly_wait(0)

            # Look for completion badge or indicator
            completion_xpath_candidates = [
                "//div[contains(@class, 'completion-header')]//span[contains(text(), 'Completed')]",
                "//div[contains(@class, 'course-completion')]//span[contains(text(), 'Completed')]",
                "//div[contains(@class, 'completionprogress')]//span[contains(text(), 'Completed')]",
                "//div[@id='completionreport']//span[contains(text(), 'Completed')]",
            ]

            driver.implicitly_wait(10)
            for xpath in completion_xpath_candidates:
                try:
                    elem = driver.find_element(By.XPATH, xpath)
                    if elem.is_displayed():
                        return "Completed"
                except NoSuchElementException:
                    pass

            driver.implicitly_wait(0)
            # If not found, assume "Not Completed"
            driver.implicitly_wait(10)
            return "Not Completed"

        except Exception:
            driver.implicitly_wait(10)
            return "No Status"

    def _is_element_present(self, driver: webdriver.Chrome, how: str, what: str):
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
                        time.sleep(2)  # Allow page to fully load

                        # Get actual completion status
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
