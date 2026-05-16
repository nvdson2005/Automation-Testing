# =============================================================
# Project #3 - Level 1: Data-Driven Automation Testing
# Feature  : FT008 - Add New User (Moodle Admin)
# Script   : Selenium WebDriver + unittest
# Data file: FT008_test_data.csv  (same folder)
# Run      : python FT008_add_user_test.py
# =============================================================

import csv
import os
import time
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


# ── Helper: resolve a Katalon-style locator to (By, value) ──
def parse_locator(locator_str: str):
    locator = locator_str.strip()
    if locator.startswith("id="):
        return By.ID, locator[3:]
    if locator.startswith("name="):
        return By.NAME, locator[5:]
    if locator.startswith("link="):
        return By.LINK_TEXT, locator[5:]
    if locator.startswith("xpath="):
        return By.XPATH, locator[6:]
    if locator.startswith("css="):
        return By.CSS_SELECTOR, locator[4:]
    return By.XPATH, locator   # default fallback


# ── Read CSV data ─────────────────────────────────────────────
def load_test_data(csv_path: str):
    rows = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


DATA_FILE = os.path.join(os.path.dirname(__file__), "FT008_test_data.csv")
SITE_URL  = "https://school.moodledemo.net/"
ADD_USER_URL = "https://school.moodledemo.net/user/editadvanced.php?id=-1"
WAIT_SEC  = 15


class FT008AddUserDataDriven(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        opts = Options()
        # opts.add_argument("--headless")          # uncomment for headless
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        cls.driver = webdriver.Chrome(options=opts)
        cls.driver.maximize_window()
        cls.wait = WebDriverWait(cls.driver, WAIT_SEC)
        cls.test_data = load_test_data(DATA_FILE)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    # ── Admin login (shared step) ─────────────────────────────
    def admin_login(self, username="manager", password="moodle26"):
        driver = self.driver
        driver.get(SITE_URL)
        
        # Click login link
        self.wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "span.login a"))).click()
        
        # Đợi DOM ổn định
        time.sleep(1.5)
        
        # Điền Username (thường Moodle Demo có thể pre-fill, nhưng nên clear và điền lại cho chắc chắn)
        try:
            uname_field = self.wait.until(EC.element_to_be_clickable((By.ID, "username")))
            uname_field = self.driver.find_element(By.ID, "username")
            uname_field.clear()
            uname_field.send_keys(username)
        except Exception:
            print("Không tìm thấy trường username hoặc đã được điền tự động.")

        # Điền Password
        pwd = self.wait.until(EC.element_to_be_clickable((By.ID, "password")))
        pwd = self.driver.find_element(By.ID, "password")
        pwd.clear()
        pwd.send_keys(password)
        
        # Submit form
        self.driver.find_element(By.ID, "login").submit()
        
        # Wait for dashboard hoặc trang chủ sau khi đăng nhập
        self.wait.until(EC.url_contains("moodledemo.net"))
        time.sleep(1) # Đợi thêm 1 chút cho trang load hẳn sau khi login

    # ── Navigate to Add-New-User form ─────────────────────────
    def go_to_add_user(self):
        self.driver.get(ADD_USER_URL)
        self.wait.until(EC.presence_of_element_located((By.ID, "id_username")))

    # ── Fill user form ────────────────────────────────────────
    def fill_user_form(self, row):
        driver, wait = self.driver, self.wait

        # Username
        uname = driver.find_element(By.ID, "id_username")
        uname.clear()
        uname.send_keys(row["username"])

        # New password (optional – only if provided)
        if row.get("new_password"):
            try:
                # Try clicking "Click to enter text" toggle first
                toggle = driver.find_elements(By.XPATH,
                    "//a[contains(., 'Click to enter text') or contains(., 'enter text')]")
                if toggle:
                    toggle[0].click()
                    time.sleep(0.5)
                pwd_field = wait.until(EC.presence_of_element_located((By.ID, "id_newpassword")))
                pwd_field.clear()
                pwd_field.send_keys(row["new_password"])
            except Exception:
                pass

        # First name
        fn = driver.find_element(By.ID, "id_firstname")
        fn.clear()
        fn.send_keys(row["firstname"])

        # Last name
        ln = driver.find_element(By.ID, "id_lastname")
        ln.clear()
        ln.send_keys(row["lastname"])

        # Email
        em = driver.find_element(By.ID, "id_email")
        em.clear()
        em.send_keys(row["email"])

    # ── Main test method (data-driven loop) ───────────────────
    def test_add_user_data_driven(self):
        self.admin_login()

        for row in self.test_data:
            tc_id    = row["TestCaseID"]
            expected = row["Expected_Result"]
            locator  = row["Assert_Element"]

            with self.subTest(test_case=tc_id):
                print(f"\n▶  Running {tc_id} ...")
                self.go_to_add_user()
                self.fill_user_form(row)

                # Submit form
                self.driver.find_element(By.ID, "id_submitbutton").click()
                time.sleep(1)

                # Assert result
                by, value = parse_locator(locator)
                try:
                    element = self.wait.until(
                        EC.presence_of_element_located((by, value))
                    )
                    actual = element.text.strip()

                    if "Changes saved" in expected:
                        self.assertIn("Changes saved", actual,
                            f"[{tc_id}] Expected 'Changes saved', got: '{actual}'")
                    else:
                        self.assertEqual(expected, actual,
                            f"[{tc_id}] Expected: '{expected}' | Got: '{actual}'")

                    print(f"   ✔  PASS  – {expected}")

                except Exception as e:
                    self.fail(f"[{tc_id}] FAIL – {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
