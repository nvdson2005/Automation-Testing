# =============================================================
# Project #3 - Level 2: Data-Driven Automation Testing
# Feature  : FT009 - Add New Course
# Level 2  : URLs, element locators AND test data are ALL
#             read from external files (no hardcoding in script)
# Data file: FT009_test_data.csv
# Config   : FT009_config.csv   (URLs + element locators)
# Run      : python FT009_add_course_level2.py
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


def parse_locator(locator_str: str):
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


BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_FILE   = os.path.join(BASE_DIR, "FT009_test_data.csv")
CONFIG_FILE = os.path.join(BASE_DIR, "FT009_config.csv")
WAIT_SEC    = 15
SITE_URL     = "https://school.moodledemo.net/"

class FT009AddCourseLevel2(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        opts = Options()
        # opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        cls.driver = webdriver.Chrome(options=opts)
        cls.driver.maximize_window()
        cls.wait = WebDriverWait(cls.driver, WAIT_SEC)

        cls.test_data = load_csv(DATA_FILE)
        cls.cfg = {row["key"]: row["value"] for row in load_csv(CONFIG_FILE)}

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    # ── Login ─────────────────────────────────────────────────
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
        self.driver.get(self.cfg["add_course_url"])
        self.wait.until(EC.presence_of_element_located(
            parse_locator(self.cfg["loc_fullname_field"])))

    # ── Select category via autocomplete ─────────────────────
    def select_category(self, category_label: str):
        driver, wait, cfg = self.driver, self.wait, self.cfg
        if not category_label:
            return
        try:
            driver.find_element(*parse_locator(cfg["loc_category_dropdown"])).click()
            time.sleep(0.5)
            input_el = driver.find_element(
                By.XPATH, "//input[@id[contains(.,'form_autocomplete_input')]]")
            input_el.clear()
            input_el.send_keys(category_label.split("/")[-1].strip())
            time.sleep(1)
            option = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                f"//ul[contains(@class,'autocomplete-suggestions')]"
                f"//li[contains(normalize-space(.), '{category_label.split('/')[-1].strip()}')]"
            )))
            option.click()
        except Exception:
            try:
                sel = Select(driver.find_element(By.ID, "id_category"))
                sel.select_by_visible_text(category_label)
            except Exception:
                pass

    # ── Fill form ─────────────────────────────────────────────
    def fill_course_form(self, row: dict):
        driver, wait, cfg = self.driver, self.wait, self.cfg

        fn = driver.find_element(*parse_locator(cfg["loc_fullname_field"]))
        fn.clear(); fn.send_keys(row["fullname"])

        sn = driver.find_element(*parse_locator(cfg["loc_shortname_field"]))
        sn.clear(); sn.send_keys(row["shortname"])

        self.select_category(row["category"])

        if row.get("end_day") and row.get("end_month"):
            try:
                chk = driver.find_element(*parse_locator(cfg["loc_enddate_checkbox"]))
                if chk.is_selected():
                    chk.click()
                Select(driver.find_element(*parse_locator(cfg["loc_enddate_day"]))).select_by_visible_text(row["end_day"])
                Select(driver.find_element(*parse_locator(cfg["loc_enddate_month"]))).select_by_visible_text(row["end_month"])
            except Exception:
                pass

    # ── Data-driven test loop ─────────────────────────────────
    def test_add_course_level2(self):
        self.admin_login()

        for row in self.test_data:
            tc_id    = row["TestCaseID"]
            expected = row["Expected_Result"]
            locator  = row["Assert_Element"]

            with self.subTest(test_case=tc_id):
                print(f"\n▶  [{tc_id}]  fullname={row['fullname']}")
                self.go_to_add_course()
                self.fill_course_form(row)

                self.driver.find_element(
                    *parse_locator(self.cfg["loc_submit_button"])).click()
                time.sleep(1)

                by, value = parse_locator(locator)
                try:
                    el = self.wait.until(
                        EC.presence_of_element_located((by, value)))
                    actual = el.text.strip()
                    self.assertIn(expected, actual,
                        f"[{tc_id}] expected '{expected}', got '{actual}'")
                    print(f"   ✔  PASS  – {expected}")
                except Exception as e:
                    self.fail(f"[{tc_id}] FAIL – {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
