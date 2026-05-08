# -*- coding: utf-8 -*-
import time
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

BASE_URL = "https://school.moodledemo.net"
USERNAME = "student"
PASSWORD = "moodle26"

# Maximum acceptable response time in seconds for any single operation
THRESHOLD_SECONDS = 5.0

# URLs under test
ASSIGNMENT_URL = f"{BASE_URL}/mod/assign/view.php?id=929"
FORUM_URL = f"{BASE_URL}/mod/forum/view.php?id=706"
COURSES_URL = f"{BASE_URL}/my/courses.php"


def _login(driver):
    driver.get(f"{BASE_URL}/login/index.php")
    driver.find_element(By.ID, "username").clear()
    driver.find_element(By.ID, "username").send_keys(USERNAME)
    driver.find_element(By.ID, "password").clear()
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.ID, "login").submit()
    WebDriverWait(driver, 30).until(EC.url_contains("/my/"))


class NFTPerformanceTest(unittest.TestCase):
    """Performance tests: measures response times for key user operations.

    Each test times a single operation and asserts it completes within
    THRESHOLD_SECONDS. Results are printed for inclusion in the report.
    """

    def setUp(self):
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(30)

    def tearDown(self):
        self.driver.quit()

    def _assert_time(self, label, elapsed):
        print(f"  [{label}] {elapsed:.3f}s (threshold: {THRESHOLD_SECONDS}s) — "
              f"{'PASS' if elapsed < THRESHOLD_SECONDS else 'FAIL'}")
        self.assertLess(
            elapsed, THRESHOLD_SECONDS,
            f"{label}: {elapsed:.3f}s exceeds threshold of {THRESHOLD_SECONDS}s"
        )

    # ── TC-NFT-01: Login response time ─────────────────────────────────────

    def test_01_login_response_time(self):
        """Time from submitting login credentials to dashboard load."""
        driver = self.driver
        driver.get(f"{BASE_URL}/login/index.php")
        driver.find_element(By.ID, "username").send_keys(USERNAME)
        driver.find_element(By.ID, "password").send_keys(PASSWORD)

        start = time.perf_counter()
        driver.find_element(By.ID, "login").submit()
        WebDriverWait(driver, 30).until(EC.url_contains("/my/"))
        elapsed = time.perf_counter() - start

        self._assert_time("Login response time", elapsed)

    # ── TC-NFT-02: Assignment page load time ───────────────────────────────

    def test_02_assignment_page_load_time(self):
        """Time to load the assignment page after login."""
        driver = self.driver
        _login(driver)

        start = time.perf_counter()
        driver.get(ASSIGNMENT_URL)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(text(),'submission')]"))
        )
        elapsed = time.perf_counter() - start

        self._assert_time("Assignment page load time", elapsed)

    # ── TC-NFT-03: Forum page load time ────────────────────────────────────

    def test_03_forum_page_load_time(self):
        """Time to load the forum page after login."""
        driver = self.driver
        _login(driver)

        start = time.perf_counter()
        driver.get(FORUM_URL)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.LINK_TEXT, "Add discussion topic"))
        )
        elapsed = time.perf_counter() - start

        self._assert_time("Forum page load time", elapsed)

    # ── TC-NFT-04: Assignment submission response time ─────────────────────

    def test_04_assignment_submission_response_time(self):
        """Time from clicking Save on assignment editor to confirmation page load."""
        driver = self.driver
        _login(driver)
        driver.get(ASSIGNMENT_URL)

        # Open editor
        WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'submission')]"))
        )
        btns = driver.find_elements(By.XPATH, "//button[contains(text(),'Add submission')]")
        if btns:
            btns[0].click()
        else:
            driver.find_element(By.XPATH, "//button[contains(text(),'Remove submission')]").click()
            driver.find_element(By.XPATH, "//button[contains(text(),'Continue')]").click()
            driver.find_element(By.XPATH, "//button[contains(text(),'Add submission')]").click()

        # Wait for TinyMCE then inject content
        WebDriverWait(driver, 30).until(lambda d: d.execute_script(
            "return typeof tinymce !== 'undefined'"
            " && tinymce.activeEditor !== null"
            " && tinymce.activeEditor.initialized === true;"
        ))
        driver.execute_script('tinymce.activeEditor.setContent("<p>Performance test submission</p>");')

        start = time.perf_counter()
        driver.find_element(By.ID, "id_submitbutton").click()
        WebDriverWait(driver, 30).until(
            EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Submitted for grading")
        )
        elapsed = time.perf_counter() - start

        self._assert_time("Assignment submission response time", elapsed)

    # ── TC-NFT-05: Forum post submission response time ─────────────────────

    def test_05_forum_post_submission_response_time(self):
        """Time from clicking Submit on forum form to confirmation page load."""
        driver = self.driver
        _login(driver)
        driver.get(FORUM_URL)

        driver.find_element(By.LINK_TEXT, "Add discussion topic").click()
        driver.find_element(By.ID, "id_subject").send_keys("Performance Test Post")

        WebDriverWait(driver, 30).until(lambda d: d.execute_script(
            "return typeof tinymce !== 'undefined'"
            " && tinymce.activeEditor !== null"
            " && tinymce.activeEditor.initialized === true;"
        ))
        driver.execute_script('tinymce.activeEditor.setContent("<p>Performance test message</p>");')

        start = time.perf_counter()
        driver.find_element(By.ID, "id_submitbutton").click()
        WebDriverWait(driver, 30).until(
            EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "successfully added")
        )
        elapsed = time.perf_counter() - start

        self._assert_time("Forum post submission response time", elapsed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
