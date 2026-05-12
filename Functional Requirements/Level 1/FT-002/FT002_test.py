# -*- coding: utf-8 -*-
import csv
import json
import os
import unittest
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoAlertPresentException, NoSuchElementException


class FT002Test(unittest.TestCase):
    """Data-driven forum post tests. Test data in FT002_data.csv.

    expected column values:
        success            – assertRegex on page body (always passes if page loads)
        error_subject      – assertTrue(id_error_subject present)
        error_message      – assertTrue(id_error_message present)
        error_both         – assertTrue both error elements present
    """

    _CSV = os.path.join(os.path.dirname(__file__), "FT002_data.csv")

    # ── helpers ────────────────────────────────────────────────────────────

    def _make_driver(self):
        driver = webdriver.Chrome()
        driver.implicitly_wait(30)
        return driver

    def _login_as_student(self, driver):
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

    def _open_forum_form(self, driver):
        driver.get("https://school.moodledemo.net/mod/forum/view.php?id=706")
        driver.find_element(By.LINK_TEXT, "Add discussion topic").click()

    def _fill_subject(self, driver, subject):
        driver.find_element(By.ID, "id_subject").clear()
        driver.find_element(By.ID, "id_subject").send_keys(subject)

    def _fill_message(self, driver, message):
        if not message:
            return
        WebDriverWait(driver, 30).until(lambda d: d.execute_script(
            "return typeof tinymce !== 'undefined'"
            " && tinymce.activeEditor !== null"
            " && tinymce.activeEditor.initialized === true;"
        ))
        driver.execute_script("tinymce.activeEditor.setContent(" + json.dumps(message) + ");")
        first_words = message[:20]
        WebDriverWait(driver, 15).until(lambda d: d.execute_script(
            "return tinymce.activeEditor.getContent().indexOf(" + json.dumps(first_words) + ") !== -1;"
        ))

    def _is_element_visible(self, driver, how, what):
        try:
            el = driver.find_element(by=how, value=what)
            return el.is_displayed()
        except NoSuchElementException:
            return False

    def _assert_result(self, driver, expected, verification_errors):
        if expected == "error_subject":
            try:
                self.assertTrue(self._is_element_visible(driver, By.ID, "id_error_subject"))
            except AssertionError as e:
                verification_errors.append(str(e))

        elif expected == "error_message":
            try:
                self.assertTrue(self._is_element_visible(driver, By.ID, "id_error_message"))
            except AssertionError as e:
                verification_errors.append(str(e))

        elif expected == "error_both":
            try:
                self.assertTrue(self._is_element_visible(driver, By.ID, "id_error_subject"))
            except AssertionError as e:
                verification_errors.append(str(e))
            try:
                self.assertTrue(self._is_element_visible(driver, By.ID, "id_error_message"))
            except AssertionError as e:
                verification_errors.append(str(e))

        else:  # success
            try:
                self.assertIn(
                    "Your post was successfully added.",
                    driver.find_element(By.TAG_NAME, "body").text,
                )
            except AssertionError as e:
                verification_errors.append(str(e))

    def _is_element_present(self, driver, how, what):
        try:
            driver.find_element(by=how, value=what)
        except NoSuchElementException:
            return False
        return True

    def _is_alert_present(self, driver):
        try:
            driver.switch_to.alert
        except NoAlertPresentException:
            return False
        return True

    def _close_alert_and_get_its_text(self, driver):
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            return alert_text
        finally:
    # ── test ───────────────────────────────────────────────────────────────

    def test_add_forum_post(self):
        with open(self._CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                with self.subTest(test_id=row["test_id"]):
                    verification_errors = []
                    driver = self._make_driver()
                    try:
                        self._login_as_student(driver)
                        self._open_forum_form(driver)
                        self._fill_subject(driver, row["subject"])
                        self._fill_message(driver, row["message"])
                        time.sleep(1)  # Buffer to allow submission to process and page to update
                        driver.find_element(By.ID, "id_submitbutton").click()
                        time.sleep(3)  # Buffer to allow submission to process and page to update
                        self._assert_result(driver, row["expected"], verification_errors)
                        self.assertEqual([], verification_errors)
                    finally:
                        driver.quit()


if __name__ == "__main__":
    unittest.main()
