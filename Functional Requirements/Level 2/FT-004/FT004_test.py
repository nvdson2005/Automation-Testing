# -*- coding: utf-8 -*-
import csv
import json
import os
import time
import unittest
from datetime import datetime
from selenium import webdriver
from selenium.common.exceptions import (
    ElementNotInteractableException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# ─── CẤU HÌNH ĐƯỜNG DẪN ──────────────────────────────────────────────────────
_DIR        = os.path.dirname(os.path.abspath(__file__))
CONFIG_CSV  = os.path.join(_DIR, "FT004_config.csv")
DATA_CSV    = os.path.join(_DIR, "FT004_data.csv")
LOG_PATH    = os.path.join(_DIR, "FT004_result_lv2.log")

# ─── ENGINE ĐỌC CẤU HÌNH ────────────────────────────────────────────────────
CONFIG = {}
with open(CONFIG_CSV, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        CONFIG[row["item_name"]] = {"type": row["selector_type"], "val": row["selector_value"]}

def get_item(name):
    return CONFIG.get(name, {"type": None, "val": None})

def get_value(name):
    return get_item(name)["val"]

def find_el(driver, name, wait=15):
    item = get_item(name)
    by = {"id": By.ID, "xpath": By.XPATH, "css": By.CSS_SELECTOR, "tag": By.TAG_NAME, "link": By.LINK_TEXT}.get(item["type"], By.ID)
    return WebDriverWait(driver, wait).until(EC.presence_of_element_located((by, item["val"])))

# ─── Logger ──────────────────────────────────────────────────────────────────
class StateLogger:
    def __init__(self, path: str):
        self._path = path
        with open(self._path, "w", encoding="utf-8") as f:
            f.write(f"# FT-004 Level 2 Run – {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")

    def log(self, tid: str, status: str, state: dict, msg: str = ""):
        entry = {"ts": datetime.now().isoformat(), "id": tid, "st": status, "msg": msg, "state": state}
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        flag = {"PASS": "✓", "FAIL": "✗", "ERROR": "!", "INFO": "·"}.get(status, "?")
        print(f"  [{flag}] {tid:15s} | {status:5s} | {msg}")

# ─── Test Class ──────────────────────────────────────────────────────────────
class FT004Level2Test(unittest.TestCase):
    _logger = None

    @classmethod
    def setUpClass(cls):
        cls._logger = StateLogger(LOG_PATH)
        cls._logger.log("LV2_START", "INFO", {}, "Bắt đầu suite Level 2 FT-004")

    def _make_driver(self):
        d = webdriver.Chrome()
        d.implicitly_wait(10)
        return d

    def _dismiss(self, driver):
        try:
            btns = driver.find_elements(By.XPATH, "//button[text()='Continue'] | //a[text()='Continue']")
            if btns: btns[0].click(); time.sleep(1)
        except (ElementNotInteractableException, StaleElementReferenceException):
            pass

    def _login(self, driver):
        driver.get(get_item("url_login")["val"])
        self._dismiss(driver)
        try:
            find_el(driver, "field_username").send_keys(get_value("username"))
            find_el(driver, "field_login_pw").send_keys(get_value("password"))
            find_el(driver, "btn_login").click()
            time.sleep(2); self._dismiss(driver)
        except (NoSuchElementException, TimeoutException, WebDriverException) as exc:
            raise AssertionError("Login failed") from exc

    def _get_count(self, driver):
        return int(driver.execute_script(get_value("visible_course_cards_js")))

    def _select_grouping(self, driver, group):
        if not group:
            return
        drop = find_el(driver, "btn_grouping")
        driver.execute_script("arguments[0].scrollIntoView();", drop)
        drop.click()
        template = get_value("group_option")
        option_xpath = template.replace("{group}", group)
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, option_xpath))).click()
        time.sleep(2)

    def _search_course(self, driver, query):
        search = find_el(driver, "field_search")
        search.clear()
        search.send_keys(query)
        search.send_keys(Keys.ENTER)
        time.sleep(4)

    def _assert_contains_course(self, driver, expected_text):
        by_val = get_item("item_course_name")
        expected = expected_text.lower()
        WebDriverWait(driver, 15).until(
            lambda active_driver: any(
                expected in result.text.lower()
                for result in active_driver.find_elements(By.CSS_SELECTOR, by_val["val"])
            )
        )

    def test_ft004_lv2_search(self):
        with open(DATA_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        for row in rows:
            tid = row["test_id"]
            with self.subTest(test_id=tid):
                driver = self._make_driver()
                self._logger.log(tid, "INFO", {"query": row["query"]}, "Bắt đầu")
                try:
                    self._login(driver)
                    driver.get(get_item("url_courses")["val"])
                    self._dismiss(driver)

                    et = row["expected_type"]
                    exp = row["expected_text"]

                    # 1. Chọn grouping và tìm kiếm. FT004008 có hai bước theo Katalon.
                    if et == "contains_each":
                        queries = row["query"].split("|")
                        groups = row["grouping"].split("|")
                        expected_values = exp.split("|")
                        self.assertEqual(len(queries), len(groups))
                        self.assertEqual(len(queries), len(expected_values))
                        for query, group, expected in zip(queries, groups, expected_values):
                            self._select_grouping(driver, group.strip())
                            self._search_course(driver, query.strip())
                            self._assert_contains_course(driver, expected.strip())
                        status, msg = "PASS", "Thành công"
                        continue

                    self._select_grouping(driver, row["grouping"])
                    self._search_course(driver, row["query"])

                    # 2. Kiểm tra kết quả
                    count = self._get_count(driver)

                    if et == "contains":
                        self._assert_contains_course(driver, exp)
                    elif et == "no_courses":
                        body = find_el(driver, "container_body").text
                        self.assertIn(get_value("no_courses_text"), body)
                    elif et == "min_visible":
                        self.assertGreaterEqual(count, int(row["min_visible"]))
                    elif et == "baseline_unchanged":
                        self.assertGreaterEqual(count, int(row["min_visible"]))

                    status, msg = "PASS", "Thành công"
                except Exception as e:
                    status, msg = "FAIL", str(e)
                    raise
                finally:
                    self._logger.log(tid, status, {"count": self._get_count(driver)}, msg)
                    driver.quit()

if __name__ == "__main__":
    unittest.main(verbosity=2)
