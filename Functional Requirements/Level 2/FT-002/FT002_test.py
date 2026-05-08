# -*- coding: utf-8 -*-
import csv
import json
import os
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoAlertPresentException, NoSuchElementException


def _load_config(path):
    with open(path, newline="", encoding="utf-8") as f:
        return {row["key"]: row["value"] for row in csv.DictReader(f)}


class FT002Test(unittest.TestCase):
    """Level 2: URLs and selectors loaded from FT002_config.csv.

    expected column values:
        success        – assertIn success_text (from config) in page body
        error_subject  – assertTrue id_error_subject (from config) visible
        error_message  – assertTrue id_error_message (from config) visible
        error_both     – assertTrue both error elements visible
    """

    _DIR = os.path.dirname(__file__)
    _CSV = os.path.join(_DIR, "FT002_data.csv")
    _CFG = os.path.join(_DIR, "FT002_config.csv")

    @classmethod
    def setUpClass(cls):
        cls.cfg = _load_config(cls._CFG)

    # ── helpers ────────────────────────────────────────────────────────────

    def _make_driver(self):
        driver = webdriver.Chrome()
        driver.implicitly_wait(30)
        return driver

    def _login_as_student(self, driver):
        driver.get(self.cfg["base_url"])
        driver.implicitly_wait(0)
        login_needed = self._is_element_present(driver, By.LINK_TEXT, self.cfg["login_link_text"])
        driver.implicitly_wait(30)
        if login_needed:
            driver.find_element(By.LINK_TEXT, self.cfg["login_link_text"]).click()
            driver.find_element(By.ID, self.cfg["username_field_id"]).clear()
            driver.find_element(By.ID, self.cfg["username_field_id"]).send_keys(self.cfg["username_value"])
            driver.find_element(By.ID, self.cfg["password_field_id"]).clear()
            driver.find_element(By.ID, self.cfg["password_field_id"]).send_keys(self.cfg["password_value"])
            driver.find_element(By.ID, self.cfg["login_form_id"]).submit()

    def _open_forum_form(self, driver):
        driver.get(self.cfg["forum_url"])
        driver.find_element(By.LINK_TEXT, self.cfg["add_discussion_link_text"]).click()

    def _fill_subject(self, driver, subject):
        driver.find_element(By.ID, self.cfg["subject_field_id"]).clear()
        driver.find_element(By.ID, self.cfg["subject_field_id"]).send_keys(subject)

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

    def _is_element_present(self, driver, how, what):
        try:
            driver.find_element(by=how, value=what)
        except NoSuchElementException:
            return False
        return True

    def _is_element_visible(self, driver, how, what):
        try:
            return driver.find_element(by=how, value=what).is_displayed()
        except NoSuchElementException:
            return False

    def _assert_result(self, driver, expected, verification_errors):
        if expected == "error_subject":
            try:
                self.assertTrue(self._is_element_visible(driver, By.ID, self.cfg["error_subject_id"]))
            except AssertionError as e:
                verification_errors.append(str(e))

        elif expected == "error_message":
            try:
                self.assertTrue(self._is_element_visible(driver, By.ID, self.cfg["error_message_id"]))
            except AssertionError as e:
                verification_errors.append(str(e))

        elif expected == "error_both":
            try:
                self.assertTrue(self._is_element_visible(driver, By.ID, self.cfg["error_subject_id"]))
            except AssertionError as e:
                verification_errors.append(str(e))
            try:
                self.assertTrue(self._is_element_visible(driver, By.ID, self.cfg["error_message_id"]))
            except AssertionError as e:
                verification_errors.append(str(e))

        else:  # success
            try:
                self.assertIn(
                    self.cfg["success_text"],
                    driver.find_element(By.TAG_NAME, "body").text,
                )
            except AssertionError as e:
                verification_errors.append(str(e))

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
                        driver.find_element(By.ID, self.cfg["submit_button_id"]).click()
                        self._assert_result(driver, row["expected"], verification_errors)
                        self.assertEqual([], verification_errors)
                    finally:
                        driver.quit()


if __name__ == "__main__":
    unittest.main()
