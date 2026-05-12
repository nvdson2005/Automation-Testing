# -*- coding: utf-8 -*-
"""
Non-functional tests for FT-004: Course Search performance and security/robustness.

Run:
    cd "Automation-Testing/Non-functional Requirements/NF-004"
    python NF-004.py
"""
import time
import unittest
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoAlertPresentException,
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)

BASE_URL = "https://school.moodledemo.net"
USERNAME = "student"
PASSWORD = os.getenv("NF004_PASSWORD", "moodle" + "26")
COURSES_URL = f"{BASE_URL}/my/courses.php"
NO_COURSES_TEXT = "No courses"

# Performance Thresholds
SEARCH_THRESHOLD = 3.0
CLEAR_THRESHOLD = 3.0

def _login(driver):
    driver.get(f"{BASE_URL}/login/index.php")
    try:
        # Dismiss policies if they appear
        btns = driver.find_elements(By.XPATH, "//button[text()='Continue'] | //a[text()='Continue']")
        if btns: btns[0].click(); time.sleep(1)
        
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username"))).send_keys(USERNAME)
        p_id = "password" if driver.find_elements(By.ID, "password") else "passwordinput"
        driver.find_element(By.ID, p_id).send_keys(PASSWORD)
        btn = "loginbtn" if driver.find_elements(By.ID, "loginbtn") else "login"
        driver.find_element(By.ID, btn).click()
        
        # Final dismiss
        btns = driver.find_elements(By.XPATH, "//button[text()='Continue'] | //a[text()='Continue']")
        if btns: btns[0].click(); time.sleep(1)
    except (NoSuchElementException, TimeoutException, WebDriverException):
        pass

def _find_search_input(driver):
    selectors = [
        (By.CSS_SELECTOR, "input[data-action='search']"),
        (By.CSS_SELECTOR, "input.form-control.withclear"),
        (By.XPATH, "//input[contains(@id, 'searchinput-')]")
    ]
    for by, val in selectors:
        try:
            el = driver.find_element(by, val)
            if el.is_displayed(): return el
        except NoSuchElementException: continue
    raise NoSuchElementException("Search input not found")

def _open_courses_page(driver):
    driver.get(COURSES_URL)
    return _find_search_input(driver)

def _perform_search(driver, query):
    search = _find_search_input(driver)
    search.clear()
    search.send_keys(query)
    start = time.perf_counter()
    search.send_keys(Keys.ENTER)
    return start

def _visible_course_count(driver):
    script = "return Array.from(document.querySelectorAll('div.col.d-flex')).filter(el => el.offsetParent !== null).length;"
    return int(driver.execute_script(script))

def _course_result_contains(driver, expected_text):
    results = driver.find_elements(By.CSS_SELECTOR, ".coursename")
    return any(expected_text.lower() in result.text.lower() for result in results)

def _wait_for_search_settle(driver, expected_text=None, timeout=10):
    def result_is_ready(active_driver):
        body_text = active_driver.find_element(By.TAG_NAME, "body").text
        if expected_text and _course_result_contains(active_driver, expected_text):
            return True
        return NO_COURSES_TEXT in body_text or _visible_course_count(active_driver) == 0

    WebDriverWait(driver, timeout).until(result_is_ready)


def _wait_for_search_idle(driver, settle_seconds=4, timeout=20):
    """Wait after a search without requiring empty results (avoids flaky early zero counts)."""
    time.sleep(settle_seconds)

    def search_ready(active_driver):
        el = _find_search_input(active_driver)
        return el.is_displayed() and el.is_enabled()

    WebDriverWait(driver, timeout).until(search_ready)

def _page_has_system_error(driver):
    body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    error_keywords = (
        "sql",
        "database error",
        "exception",
        "traceback",
        "syntax error",
        "stack trace",
    )
    return any(keyword in body_text for keyword in error_keywords)

def _assert_search_ui_healthy(test_case, driver):
    test_case.assertIn("/my/courses.php", driver.current_url)
    test_case.assertTrue(_find_search_input(driver).is_displayed())
    test_case.assertTrue(driver.find_element(By.TAG_NAME, "body").text.strip())
    test_case.assertFalse(_page_has_system_error(driver), "System error text was shown on the page")

class FT004NonFunctionalTest(unittest.TestCase):
    """Combined Performance and Security/Robustness tests for FT-004."""

    driver = None

    @classmethod
    def setUpClass(cls):
        cls.driver = webdriver.Chrome()
        cls.driver.implicitly_wait(10)
        _login(cls.driver)
        _open_courses_page(cls.driver)

    @classmethod
    def tearDownClass(cls):
        if cls.driver is not None:
            cls.driver.quit()
            cls.driver = None

    def _get_visible_count(self, driver):
        return _visible_course_count(driver)

    # ─── PHẦN 1: PERFORMANCE TESTING ──────────────────────────────────────────

    def test_01_search_response_time(self):
        """Đo thời gian phản hồi khi tìm kiếm khoá học."""
        driver = self.driver

        start = _perform_search(driver, "Digital")
        _wait_for_search_settle(driver, expected_text="Digital Literacy")
        elapsed = time.perf_counter() - start

        print(f"\n  [Performance] Search time: {elapsed:.3f}s (Threshold: {SEARCH_THRESHOLD}s)")
        self.assertLess(elapsed, SEARCH_THRESHOLD)

    # ─── PHẦN 2: SECURITY & ROBUSTNESS TESTING ────────────────────────────────

    def test_02_search_security_sql_injection(self):
        """Kiểm tra chống tấn công SQL Injection trong ô Search."""
        driver = self.driver

        payload = "' OR 1=1 --"
        _perform_search(driver, payload)
        _wait_for_search_settle(driver)

        body_text = driver.find_element(By.TAG_NAME, "body").text
        _assert_search_ui_healthy(self, driver)
        self.assertFalse(_page_has_system_error(driver), "System showed SQL/database error text")
        self.assertTrue(NO_COURSES_TEXT in body_text or self._get_visible_count(driver) == 0)
        print("  [Security] SQL Injection handled safely.")

    def test_03_search_security_xss(self):
        """Kiểm tra chống tấn công Cross-Site Scripting (XSS)."""
        driver = self.driver

        payload = "<script>alert('XSS')</script>"
        _perform_search(driver, payload)
        _wait_for_search_settle(driver)

        # Kiểm tra xem alert có hiện ra không (nếu hiện là FAIL)
        try:
            alert = driver.switch_to.alert
            alert.dismiss()
            self.fail("XSS payload executed! System is vulnerable.")
        except NoAlertPresentException:
            # Không có alert là PASS
            _assert_search_ui_healthy(self, driver)
            print("  [Security] XSS payload handled safely.")

    def test_04_search_robustness_long_query(self):
        """Kiểm tra độ bền với chuỗi tìm kiếm cực dài."""
        driver = self.driver

        payload = "A" * 500  # Chuỗi 500 ký tự
        _perform_search(driver, payload)
        # Không dùng _wait_for_search_settle(...): với chuỗi rất dài, Moodle có thể vẫn hiển thị
        # khóa học đã đăng ký (không có chữ "No courses") hoặc số card tạm = 0 rồi render lại → flaky.
        _wait_for_search_idle(driver)

        # Hệ thống phải xử lý mượt mà, không bị treo; ô search vẫn dùng được sau tìm kiếm
        _assert_search_ui_healthy(self, driver)
        search = _find_search_input(driver)
        self.assertTrue(search.is_enabled(), "Search box should remain interactive after long query")
        search.clear()
        search.send_keys("x")
        self.assertIn("x", (search.get_attribute("value") or "").lower())
        print("  [Robustness] Long query handled without system failure.")

if __name__ == "__main__":
    unittest.main(verbosity=2)
