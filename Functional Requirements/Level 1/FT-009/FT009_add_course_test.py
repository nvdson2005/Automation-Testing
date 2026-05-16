# =============================================================
# Project #3 - Level 1: Data-Driven Automation Testing
# Feature  : FT009 - Add New Course (Moodle Admin)
# Script   : Selenium WebDriver + unittest
# Data file: FT009_test_data.csv  (same folder)
# Run      : python FT009_add_course_test.py
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


# ── Helper: resolve a Katalon-style locator ───────────────────
def parse_locator(locator_str: str):
    loc = locator_str.strip()
    if loc.startswith("id="):
        return By.ID, loc[3:]
    if loc.startswith("name="):
        return By.NAME, loc[5:]
    if loc.startswith("link="):
        return By.LINK_TEXT, loc[5:]
    if loc.startswith("xpath="):
        return By.XPATH, loc[6:]
    if loc.startswith("css="):
        return By.CSS_SELECTOR, loc[4:]
    return By.XPATH, loc


# ── Read CSV data ─────────────────────────────────────────────
def load_test_data(csv_path: str):
    rows = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


DATA_FILE    = os.path.join(os.path.dirname(__file__), "FT009_test_data.csv")
SITE_URL     = "https://school.moodledemo.net/"
ADD_COURSE_URL = "https://school.moodledemo.net/course/edit.php?category=0"
WAIT_SEC     = 15


class FT009AddCourseDataDriven(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        opts = Options()
        # opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        cls.driver = webdriver.Chrome(options=opts)
        cls.driver.maximize_window()
        cls.wait   = WebDriverWait(cls.driver, WAIT_SEC)
        cls.test_data = load_test_data(DATA_FILE)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    # ── Admin login ───────────────────────────────────────────
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

    # ── Navigate to Add-Course form ───────────────────────────
    def go_to_add_course(self):
        self.driver.get(ADD_COURSE_URL)
        self.wait.until(EC.presence_of_element_located((By.ID, "id_fullname")))

    # ── Select category via autocomplete ─────────────────────
    def select_category(self, category_label: str):
        driver, wait = self.driver, self.wait
        if not category_label:
            return
        try:
            # Open the autocomplete dropdown
            dropdown_btn = driver.find_element(
                By.XPATH, "//span[contains(@class,'form-autocomplete-downarrow')]")
            dropdown_btn.click()
            time.sleep(0.5)
            # Type to filter
            input_el = driver.find_element(
                By.XPATH, "//input[@id[contains(.,'form_autocomplete_input')]]")
            input_el.clear()
            input_el.send_keys(category_label.split("/")[-1].strip())
            time.sleep(1)
            # Click matching option
            option = wait.until(EC.element_to_be_clickable(
                (By.XPATH,
                 f"//ul[contains(@class,'autocomplete-suggestions')]"
                 f"//li[contains(normalize-space(.), '{category_label.split('/')[-1].strip()}')]"
                )))
            option.click()
        except Exception:
            # Fallback: standard select
            try:
                sel = Select(driver.find_element(By.ID, "id_category"))
                sel.select_by_visible_text(category_label)
            except Exception:
                pass

    # ── Fill course form ──────────────────────────────────────
    def fill_course_form(self, row):
        driver, wait = self.driver, self.wait

        # Full name
        fn = driver.find_element(By.ID, "id_fullname")
        fn.clear()
        fn.send_keys(row["fullname"])

        # Short name
        sn = driver.find_element(By.ID, "id_shortname")
        sn.clear()
        sn.send_keys(row["shortname"])

        # Category
        self.select_category(row["category"])

        # End date (only for TC-001)
        if row.get("end_day") and row.get("end_month"):
            try:
                chk = driver.find_element(By.ID, "id_automaticenddate")
                if chk.is_selected():
                    chk.click()   # uncheck "compute automatically"
                Select(driver.find_element(By.ID, "id_enddate_day")).select_by_visible_text(row["end_day"])
                Select(driver.find_element(By.ID, "id_enddate_month")).select_by_visible_text(row["end_month"])
            except Exception:
                pass

    # ── Main data-driven loop ─────────────────────────────────
    def test_add_course_data_driven(self):
        self.admin_login()

        for row in self.test_data:
            tc_id    = row["TestCaseID"]
            expected = row["Expected_Result"]
            locator  = row["Assert_Element"]

            with self.subTest(test_case=tc_id):
                print(f"\n▶  Running {tc_id} ...")
                self.go_to_add_course()
                self.fill_course_form(row)

                # Submit
                self.driver.find_element(By.ID, "id_saveanddisplay").click()
                time.sleep(1)

                by, value = parse_locator(locator)
                try:
                    element = self.wait.until(
                        EC.presence_of_element_located((by, value))
                    )
                    actual = element.text.strip()

                    # Verify
                    self.assertIn(expected, actual,
                        f"[{tc_id}] Expected: '{expected}' | Got: '{actual}'")
                    print(f"   ✔  PASS  – {expected}")

                except Exception as e:
                    self.fail(f"[{tc_id}] FAIL – {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
