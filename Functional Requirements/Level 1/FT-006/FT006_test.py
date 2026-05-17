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


class FT006Test(unittest.TestCase):
    """Data-driven user picture upload tests. Test data in FT006_data.csv."""

    _CSV = os.path.join(os.path.dirname(__file__), "FT006_data.csv")

    # ── helpers ────────────────────────────────────────────────────────────

    def _make_driver(self) -> webdriver.Chrome:
        driver = webdriver.Chrome()
        driver.implicitly_wait(30)
        return driver

    def _login(self, driver: webdriver.Chrome, username: str, password: str):
        driver.get("https://school.moodledemo.net/")
        driver.implicitly_wait(0)
        login_needed = self._is_element_present(driver, By.LINK_TEXT, "Log in")
        driver.implicitly_wait(30)
        if login_needed:
            driver.find_element(By.LINK_TEXT, "Log in").click()
            driver.find_element(By.ID, "username").clear()
            driver.find_element(By.ID, "username").send_keys(username)
            driver.find_element(By.ID, "password").clear()
            driver.find_element(By.ID, "password").send_keys(password)
            driver.find_element(By.ID, "login").submit()
        WebDriverWait(driver, 30).until(EC.url_contains("moodledemo.net"))

    def _navigate_to_edit_profile(self, driver: webdriver.Chrome):
        """Navigate to profile edit page."""
        if "manager" in driver.current_url or "admin" in driver.current_url:
            # Manager flow: Site Admin > Users > Browse > Select > Edit Profile
            driver.get("https://school.moodledemo.net/admin/index.php")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(1)
            # Look for users management link
            try:
                users_link = driver.find_element(By.LINK_TEXT, "Users")
                users_link.click()
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.LINK_TEXT, "Browse list of users")))
                driver.find_element(By.LINK_TEXT, "Browse list of users").click()
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "table")))
                time.sleep(1)
                # Select first user and edit
                user_row = driver.find_elements(By.XPATH, "//table//tr[contains(@class, 'datarow')]")
                if user_row:
                    user_row[0].click()
                    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.LINK_TEXT, "Edit profile")))
                    driver.find_element(By.LINK_TEXT, "Edit profile").click()
            except NoSuchElementException:
                pass
        else:
            # Student/Teacher flow: Profile > Edit profile
            driver.get("https://school.moodledemo.net/user/profile.php")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            try:
                driver.find_element(By.LINK_TEXT, "Edit profile").click()
            except NoSuchElementException:
                # Try alternative method
                driver.get("https://school.moodledemo.net/user/edit.php?id=self")

        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "id_firstname")))

    def _scroll_to_picture_section(self, driver: webdriver.Chrome):
        """Scroll to user picture section."""
        driver.execute_script("""
            var elem = document.querySelector('[data-fieldname="picture"]') ||
                       document.querySelector('.fitem.picture') ||
                       document.querySelector('input[name="userfile"]')?.closest('fieldset');
            if (elem) elem.scrollIntoView(true);
        """)
        time.sleep(1)

    def _upload_file(self, driver: webdriver.Chrome, file_path: str):
        """Upload a file to user picture input."""
        if not file_path or file_path.lower() == "none":
            return False
        try:
            file_input = driver.find_element(By.XPATH, "//input[@type='file' and @name='userfile']")
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

    def _set_description(self, driver: webdriver.Chrome, description: str):
        """Set picture description."""
        if not description or description.lower() == "none":
            return
        try:
            desc_field = driver.find_element(By.ID, "id_picture")
            if desc_field:
                desc_field.clear()
                desc_field.send_keys(description)
        except NoSuchElementException:
            pass

    def _get_error_message(self, driver: webdriver.Chrome) -> str:
        """Get error message from page if present."""
        try:
            error_elem = driver.find_element(By.XPATH, "//div[@class='alert alert-danger']")
            return error_elem.text
        except NoSuchElementException:
            try:
                error_elem = driver.find_element(By.CLASS_NAME, "error")
                return error_elem.text
            except NoSuchElementException:
                return ""

    def _get_success_message(self, driver: webdriver.Chrome) -> str:
        """Get success message from page."""
        try:
            success_elem = driver.find_element(By.XPATH, "//div[@role='alert' and contains(@class, 'alert-success')]")
            return success_elem.text
        except NoSuchElementException:
            return ""

    def _is_element_present(self, driver: webdriver.Chrome, how: str, what: str):
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

                        # Upload file if provided
                        if row.get("file_path") and row["file_path"].lower() != "none":
                            self._upload_file(driver, row["file_path"])

                        # Set description if provided
                        if row.get("description") and row["description"].lower() != "none":
                            self._set_description(driver, row["description"])

                        # Handle special actions (delete, etc)
                        if row.get("action") == "delete_picture":
                            try:
                                delete_checkbox = driver.find_element(By.ID, "id_picture_delete")
                                delete_checkbox.click()
                            except NoSuchElementException:
                                pass

                        # Submit form
                        time.sleep(1)
                        driver.find_element(By.ID, "id_submitbutton").click()
                        time.sleep(2)

                        # Verify result
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
