# -*- coding: utf-8 -*-
import csv
import json
import os
import time
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoAlertPresentException, NoSuchElementException


def _load_config(path):
    with open(path, newline="", encoding="utf-8") as f:
        return {row["key"]: row["value"] for row in csv.DictReader(f)}


class FT001Test(unittest.TestCase):
    """Level 2: URLs and selectors loaded from FT001_config.csv."""

    _DIR = os.path.dirname(__file__)
    _CSV = os.path.join(_DIR, "FT001_data.csv")
    _CFG = os.path.join(_DIR, "FT001_config.csv")

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
        driver.get(self.cfg["courses_url"])

    def _open_submission_editor(self, driver, course_id, submission_id):
        course_url = self.cfg["course_url_template"] + course_id
        submission_url = self.cfg["submission_url_template"] + submission_id

        course_btn = driver.find_element(By.XPATH, f"//a[@href='{course_url}']")
        if course_btn.is_displayed():
            course_btn.click()
        else:
            driver.get(course_url)

        sub_btn = driver.find_element(By.XPATH, f"//a[@href='{submission_url}']")
        if sub_btn.is_displayed():
            sub_btn.click()
        else:
            driver.get(submission_url)

        add_text = self.cfg["add_submission_text"]
        remove_text = self.cfg["remove_submission_text"]
        continue_text = self.cfg["continue_text"]
        add_xpath = f"//button[contains(text(),'{add_text}')]"
        remove_xpath = f"//button[contains(text(),'{remove_text}')]"
        continue_xpath = f"//button[contains(text(),'{continue_text}')]"

        driver.implicitly_wait(0)
        add_exists = self._is_element_present(driver, By.XPATH, add_xpath)
        driver.implicitly_wait(10)

        if add_exists:
            driver.find_element(By.XPATH, add_xpath).click()
        else:
            driver.find_element(By.XPATH, remove_xpath).click()
            driver.find_element(By.XPATH, continue_xpath).click()
            driver.find_element(By.XPATH, add_xpath).click()

    def _set_body_text(self, driver, body_text):
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

    def _is_element_present(self, driver, how, what):
        try:
            driver.find_element(by=how, value=what)
        except NoSuchElementException:
            return False
        return True

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
                        time.sleep(1)
                        driver.find_element(By.ID, self.cfg["submit_button_id"]).click()
                        time.sleep(3)
                        try:
                            self.assertIn(row["expected"], driver.find_element(By.TAG_NAME, "body").text)
                        except AssertionError as e:
                            verification_errors.append(str(e))
                        self.assertEqual([], verification_errors)
                    except NoSuchElementException:
                        driver.save_screenshot(f"fail_{row['test_id']}.png")
                        print(f"\n[FAIL {row['test_id']}] URL: {driver.current_url}")
                        raise
                    finally:
                        driver.quit()


if __name__ == "__main__":
    unittest.main()
