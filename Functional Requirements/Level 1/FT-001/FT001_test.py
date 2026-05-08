# -*- coding: utf-8 -*-
import csv
import json
import os
import time
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoAlertPresentException, NoSuchElementException


class FT001Test(unittest.TestCase):
    """Data-driven text submission tests. Test data in FT001_data.csv."""

    _CSV = os.path.join(os.path.dirname(__file__), "FT001_data.csv")

    # ── helpers ────────────────────────────────────────────────────────────

    def _make_driver(self) -> webdriver.Chrome:
        driver = webdriver.Chrome()
        driver.implicitly_wait(30)
        return driver

    def _login_as_student(self, driver: webdriver.Chrome):
        driver.get("https://school.moodledemo.net/")
        if self._is_element_present(driver, By.LINK_TEXT, "Log in"):
            driver.find_element(By.LINK_TEXT, "Log in").click()
            driver.find_element(By.ID, "username").clear()
            driver.find_element(By.ID, "username").send_keys("student")
            driver.find_element(By.ID, "password").clear()
            driver.find_element(By.ID, "password").send_keys("moodle26")
            driver.find_element(By.ID, "login").submit()
        driver.get("https://school.moodledemo.net/my/courses.php")

    def _open_submission_editor(self, driver: webdriver.Chrome, course_id: str, submission_id: str):
        course_button = driver.find_element(
            By.XPATH,
            f"//a[@href='https://school.moodledemo.net/course/view.php?id={course_id}']",
        )
        if course_button.is_displayed():
            course_button.click()
        else:
            driver.get(f"https://school.moodledemo.net/course/view.php?id={course_id}")
        submission_button = driver.find_element(
            By.XPATH, f"//a[@href='https://school.moodledemo.net/mod/assign/view.php?id={submission_id}']"
        )
        if submission_button.is_displayed():
            submission_button.click()
        else:
            driver.get(f"https://school.moodledemo.net/mod/assign/view.php?id={submission_id}") 

        driver.implicitly_wait(0)
        add_exists = self._is_element_present(
            driver, By.XPATH, "//button[contains(text(),'Add submission')]"
        )
        driver.implicitly_wait(10)

        if add_exists:
            driver.find_element(By.XPATH, "//button[contains(text(),'Add submission')]").click()
        else:
            driver.find_element(By.XPATH, "//button[contains(text(),'Remove submission')]").click()
            driver.find_element(By.XPATH, "//button[contains(text(),'Continue')]").click()
            driver.find_element(By.XPATH, "//button[contains(text(),'Add submission')]").click()

    def _set_body_text(self, driver: webdriver.Chrome, body_text: str):
        if not body_text:
            return
        WebDriverWait(driver, 30).until(lambda d: d.execute_script(
            "return typeof tinymce !== 'undefined'"
            " && tinymce.activeEditor !== null"
            " && tinymce.activeEditor.initialized === true;"
        ))
        driver.execute_script(
            "tinymce.activeEditor.setContent(" + json.dumps(body_text) + ");"
        )
        first_words = body_text[:20]
        WebDriverWait(driver, 15).until(lambda d: d.execute_script(
            "return tinymce.activeEditor.getContent().indexOf(" + json.dumps(first_words) + ") !== -1;"
        ))

    def _is_element_present(self, driver: webdriver.Chrome, how: str, what: str):
        try:
            driver.find_element(by=how, value=what)
        except NoSuchElementException:
            return False
        return True

    def _is_alert_present(self, driver: webdriver.Chrome):
        try:
            driver.switch_to.alert
        except NoAlertPresentException:
            return False
        return True

    def _close_alert_and_get_its_text(self, driver: webdriver.Chrome):
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            return alert_text
        finally:
            pass

    # ── test ───────────────────────────────────────────────────────────────

    def test_text_submission(self):
        with open(self._CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                with self.subTest(test_id=row["test_id"]):
                    verification_errors = []
                    driver = self._make_driver()
                    try:
                        self._login_as_student(driver)
                        self._open_submission_editor(driver, row["course_id"], row["submission_id"])
                        self._set_body_text(driver, row["body_text"])
                        time.sleep(1)  # Buffer to allow submission to process and page to update
                        driver.find_element(By.ID, "id_submitbutton").click()
                        time.sleep(3)  # Buffer to allow submission to process and page to update
                        try:
                            print("Verifying submission...")
                            self.assertIn(row['expected'], driver.find_element(By.TAG_NAME, "body").text)
                            print(f"Test {row['test_id']} passed.")
                        except AssertionError as e:
                            verification_errors.append(str(e))
                        self.assertEqual([], verification_errors)
                    except NoSuchElementException as e:
                        driver.save_screenshot(f"fail_{row['test_id']}.png")
                        print(f"\n[FAIL {row['test_id']}] URL: {driver.current_url}")
                        print(f"[FAIL {row['test_id']}] Title: {driver.title}")
                        raise
                    finally:
                        driver.quit()


if __name__ == "__main__":
    unittest.main()
