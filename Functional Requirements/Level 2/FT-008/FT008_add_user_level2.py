# =============================================================
# Project #3 - Level 2: Data-Driven Automation Testing
# Feature  : FT008 - Add New User
# Level 2  : URLs, element locators AND test data are ALL
#             read from external files (no hardcoding in script)
# Data file: FT008_test_data.csv
# Config   : FT008_config.csv   (URLs + element locators)
# Run      : python FT008_add_user_level2.py
# =============================================================

import csv
import os
import time
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


# ─────────────────────────────────────────────────────────────
# 1.  HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────

def parse_locator(locator_str: str):
    """Convert 'id=xxx' / 'xpath=...' / 'css=...' to (By, value)."""
    loc = locator_str.strip()
    if loc.startswith("id="):       return By.ID,           loc[3:]
    if loc.startswith("name="):     return By.NAME,         loc[5:]
    if loc.startswith("link="):     return By.LINK_TEXT,    loc[5:]
    if loc.startswith("xpath="):    return By.XPATH,        loc[6:]
    if loc.startswith("css="):      return By.CSS_SELECTOR, loc[4:]
    return By.XPATH, loc


def load_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ─────────────────────────────────────────────────────────────
# 2.  FILE PATHS
# ─────────────────────────────────────────────────────────────

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_FILE  = os.path.join(BASE_DIR, "FT008_test_data.csv")
CONFIG_FILE = os.path.join(BASE_DIR, "FT008_config.csv")
WAIT_SEC   = 15
SITE_URL     = "https://school.moodledemo.net/"

# ─────────────────────────────────────────────────────────────
# 3.  TEST CLASS
# ─────────────────────────────────────────────────────────────

class FT008AddUserLevel2(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        opts = Options()
        # opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        cls.driver = webdriver.Chrome(options=opts)
        cls.driver.maximize_window()
        cls.wait = WebDriverWait(cls.driver, WAIT_SEC)

        # Load external files
        cls.test_data = load_csv(DATA_FILE)
        cfg_rows = load_csv(CONFIG_FILE)

        # Build a dict  key -> value  from config
        cls.cfg = {row["key"]: row["value"] for row in cfg_rows}

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    # ── Admin login using config locators ─────────────────────
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

    # ── Navigate to Add-User form ─────────────────────────────
    def go_to_add_user(self):
        self.driver.get(self.cfg["add_user_url"])
        self.wait.until(EC.presence_of_element_located(
            parse_locator(self.cfg["loc_username_field"])))

    # ── Fill form using config locators ──────────────────────
    def fill_user_form(self, row: dict):
        driver, wait, cfg = self.driver, self.wait, self.cfg

        # Username
        el = driver.find_element(*parse_locator(cfg["loc_username_field"]))
        el.clear(); el.send_keys(row["username"])

        # New password (optional)
        if row.get("new_password"):
            try:
                toggles = driver.find_elements(
                    By.XPATH,
                    "//a[contains(., 'Click to enter text') or .//em]")
                if toggles:
                    toggles[0].click()
                    time.sleep(0.4)
                pwd_el = wait.until(EC.presence_of_element_located(
                    parse_locator(cfg["loc_newpassword_field"])))
                pwd_el.clear()
                pwd_el.send_keys(row["new_password"])
            except Exception:
                pass

        # First name
        el = driver.find_element(*parse_locator(cfg["loc_firstname_field"]))
        el.clear(); el.send_keys(row["firstname"])

        # Last name
        el = driver.find_element(*parse_locator(cfg["loc_lastname_field"]))
        el.clear(); el.send_keys(row["lastname"])

        # Email
        el = driver.find_element(*parse_locator(cfg["loc_email_field"]))
        el.clear(); el.send_keys(row["email"])

    # ── Data-driven test loop ─────────────────────────────────
    def test_add_user_level2(self):
        self.admin_login(self.cfg["admin_password"])

        for row in self.test_data:
            tc_id    = row["TestCaseID"]
            expected = row["Expected_Result"]
            locator  = row["Assert_Element"]

            with self.subTest(test_case=tc_id):
                print(f"\n▶  [{tc_id}]  username={row['username']}")
                self.go_to_add_user()
                self.fill_user_form(row)

                # Submit
                submit_btn = self.driver.find_element(
                    *parse_locator(self.cfg["loc_submit_button"]))
                submit_btn.click()
                time.sleep(1)

                # Verify
                by, value = parse_locator(locator)
                try:
                    el = self.wait.until(
                        EC.presence_of_element_located((by, value)))
                    actual = el.text.strip()

                    if "Changes saved" in expected:
                        self.assertIn("Changes saved", actual,
                            f"[{tc_id}] expected 'Changes saved', got '{actual}'")
                    else:
                        self.assertEqual(expected, actual,
                            f"[{tc_id}] expected '{expected}', got '{actual}'")

                    print(f"   ✔  PASS  – {expected}")
                except Exception as e:
                    self.fail(f"[{tc_id}] FAIL – {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
