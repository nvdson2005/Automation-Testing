# -*- coding: utf-8 -*-
import csv
import json
import os
import time
import unittest
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    ElementNotInteractableException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)

# ─── Cấu hình ───────────────────────────────────────────────────────────────
USERNAME      = "student"
PASSWORD      = os.getenv("FT004_PASSWORD", "moodle" + "26")
BASE_URL      = "https://school.moodledemo.net"
LOGIN_URL     = f"{BASE_URL}/login/index.php"
COURSES_URL   = f"{BASE_URL}/my/courses.php"

_DIR          = os.path.dirname(os.path.abspath(__file__))
CSV_PATH      = os.path.join(_DIR, "FT004_data.csv")
LOG_PATH      = os.path.join(_DIR, "FT004_result.log")

# ─── Logger ──────────────────────────────────────────────────────────────────
class StateLogger:
    def __init__(self, path: str):
        self._path = path
        with open(self._path, "w", encoding="utf-8") as f:
            f.write(f"# FT-004 Course Search Run – {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")

    def log(self, tid: str, status: str, state: dict, msg: str = ""):
        entry = {"ts": datetime.now().isoformat(), "id": tid, "st": status, "msg": msg, "state": state}
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        flag = {"PASS": "✓", "FAIL": "✗", "ERROR": "!", "INFO": "·"}.get(status, "?")
        print(f"  [{flag}] {tid:12s} | {status:5s} | {msg}")

# ─── Test Class ──────────────────────────────────────────────────────────────
class FT004CourseSearchTest(unittest.TestCase):
    _logger = None

    @classmethod
    def setUpClass(cls):
        cls._logger = StateLogger(LOG_PATH)
        cls._logger.log("START", "INFO", {}, "Bắt đầu suite FT-004")

    @staticmethod
    def _make_driver():
        options = webdriver.ChromeOptions()
        # options.add_argument("--headless")
        d = webdriver.Chrome(options=options)
        d.implicitly_wait(10)
        return d

    def _dismiss(self, driver):
        """Xử lý các màn hình chính sách (Continue)."""
        try:
            for _ in range(2):
                btns = driver.find_elements(By.XPATH, "//button[normalize-space(.)='Continue'] | //a[normalize-space(.)='Continue']")
                if btns and btns[0].is_displayed():
                    btns[0].click()
                    time.sleep(1)
        except (ElementNotInteractableException, StaleElementReferenceException):
            pass

    def _login(self, driver):
        driver.get(LOGIN_URL)
        self._dismiss(driver)
        try:
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "username"))).send_keys(USERNAME)
            p_id = "password" if driver.find_elements(By.ID, "password") else "passwordinput"
            driver.find_element(By.ID, p_id).send_keys(PASSWORD)
            btn = "loginbtn" if driver.find_elements(By.ID, "loginbtn") else "login"
            driver.find_element(By.ID, btn).click()
            time.sleep(2)
            self._dismiss(driver)
        except (NoSuchElementException, TimeoutException, WebDriverException) as e:
            raise AssertionError(f"Đăng nhập thất bại: {e}")

    def _get_visible_count(self, driver):
        script = "return Array.from(document.querySelectorAll('div.col.d-flex')).filter(el => el.offsetParent !== null).length;"
        try: return int(driver.execute_script(script))
        except WebDriverException: return 0

    def _find_search_input(self, driver):
        """Tìm ô Search bằng nhiều selector fallback."""
        selectors = [
            (By.CSS_SELECTOR, "input[data-action='search']"),
            (By.CSS_SELECTOR, "input.form-control.withclear"),
            (By.XPATH, "//input[contains(@id, 'searchinput-')]"),
            (By.XPATH, "//div[contains(@class, 'searchbar')]//input")
        ]
        for by, val in selectors:
            try:
                el = driver.find_element(by, val)
                if el.is_displayed(): return el
            except NoSuchElementException: continue
        raise NoSuchElementException("Không tìm thấy ô Search bằng bất kỳ selector nào.")

    def _select_grouping(self, driver, grouping):
        if not grouping:
            return
        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "groupingdropdown")))
            drop = driver.find_element(By.ID, "groupingdropdown")
            driver.execute_script("arguments[0].scrollIntoView();", drop)
            drop.click()
            item = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.LINK_TEXT, grouping)))
            item.click()
            time.sleep(2)
        except (NoSuchElementException, TimeoutException, WebDriverException):
            pass

    def _search_course(self, driver, query):
        search_input = self._find_search_input(driver)
        search_input.clear()
        search_input.send_keys(query)
        search_input.send_keys(Keys.ENTER)
        time.sleep(5)

    def _assert_contains_course(self, driver, expected_text):
        expected = expected_text.lower()
        WebDriverWait(driver, 15).until(
            lambda active_driver: any(
                expected in result.text.lower()
                for result in active_driver.find_elements(By.CSS_SELECTOR, ".coursename")
            ),
            f"Không thấy '{expected_text}' trong kết quả",
        )

    def test_ft004_course_search(self):
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        
        for row in rows:
            tid = row["test_id"].strip()
            query = row["query"].strip()
            grouping = row["grouping"].strip()
            
            with self.subTest(test_id=tid):
                driver = self._make_driver()
                self._logger.log(tid, "INFO", {"query": query, "grouping": grouping}, "Bắt đầu")
                try:
                    self._login(driver)
                    driver.get(COURSES_URL)
                    self._dismiss(driver)

                    et = row["expected_type"].strip()
                    exp = row["expected_text"].strip()

                    # 1. Chọn Grouping và tìm kiếm. FT004008 có 2 bước theo Katalon: All -> In progress.
                    if et == "contains_each":
                        queries = query.split("|")
                        groupings = grouping.split("|")
                        expected_values = exp.split("|")
                        self.assertEqual(len(queries), len(groupings))
                        self.assertEqual(len(queries), len(expected_values))
                        for step_query, step_grouping, step_expected in zip(queries, groupings, expected_values):
                            self._select_grouping(driver, step_grouping.strip())
                            self._search_course(driver, step_query.strip())
                            self._assert_contains_course(driver, step_expected.strip())
                        status, msg = "PASS", "Thành công"
                        continue

                    self._select_grouping(driver, grouping)
                    self._search_course(driver, query)
                    current_count = self._get_visible_count(driver)

                    # 2. Kiểm tra kết quả
                    if et == "contains":
                        self._assert_contains_course(driver, exp)
                    elif et == "no_courses":
                        body = driver.find_element(By.TAG_NAME, "body").text
                        self.assertTrue("No courses" in body or current_count == 0, "Mong đợi thông báo 'No courses'")
                    elif et == "min_visible":
                        min_v = int(row["min_visible"] or 0)
                        self.assertGreaterEqual(current_count, min_v, f"Số lượng khoá học ({current_count}) ít hơn mức tối thiểu ({min_v})")
                    elif et == "baseline_unchanged":
                        self.assertGreater(current_count, 0, "Không thấy khoá học nào được hiển thị")

                    status, msg = "PASS", "Thành công"
                except Exception as e:
                    status, msg = "FAIL", str(e)
                    raise
                finally:
                    self._logger.log(tid, status, {"count": self._get_visible_count(driver)}, msg)
                    driver.quit()

if __name__ == "__main__":
    unittest.main(verbosity=2)
