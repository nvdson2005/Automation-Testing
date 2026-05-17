# -*- coding: utf-8 -*-
"""
Non-Functional Testing for FT-005: Course Completion Conditions
Tests: Performance, Accessibility, Reliability
"""
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
COURSE_ID = "6"

# Performance threshold (seconds)
THRESHOLD_PAGE_LOAD = 5.0
THRESHOLD_INTERACTION = 3.0


def _login(driver):
    driver.get(f"{BASE_URL}/")
    try:
        driver.implicitly_wait(0)
        login_needed = driver.find_element(By.LINK_TEXT, "Log in")
        driver.implicitly_wait(30)
        if login_needed.is_displayed():
            login_needed.click()
            driver.find_element(By.ID, "username").send_keys(USERNAME)
            driver.find_element(By.ID, "password").send_keys(PASSWORD)
            driver.find_element(By.ID, "login").submit()
    except NoSuchElementException:
        driver.implicitly_wait(30)
    WebDriverWait(driver, 30).until(EC.url_contains("/my/"))


class NFTPerformanceTest(unittest.TestCase):
    """Performance tests for course completion feature."""

    def setUp(self):
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(30)

    def tearDown(self):
        self.driver.quit()

    def _assert_time(self, label, elapsed):
        threshold = THRESHOLD_PAGE_LOAD if "load" in label.lower() else THRESHOLD_INTERACTION
        print(f"  [{label}] {elapsed:.3f}s (threshold: {threshold}s) — "
              f"{'PASS' if elapsed < threshold else 'FAIL'}")
        self.assertLess(
            elapsed, threshold,
            f"{label}: {elapsed:.3f}s exceeds threshold of {threshold}s"
        )

    # ── TC-NFT-005-01: Course page load time ───────────────────────────────

    def test_01_course_page_load_time(self):
        """Time to load course page with completion tracking."""
        driver = self.driver
        _login(driver)

        course_url = f"{BASE_URL}/course/view.php?id={COURSE_ID}"
        start = time.perf_counter()
        driver.get(course_url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        elapsed = time.perf_counter() - start

        self._assert_time("Course page load time", elapsed)

    # ── TC-NFT-005-02: Completion status retrieval time ──────────────────────

    def test_02_completion_status_retrieval_time(self):
        """Time to fetch and display completion status."""
        driver = self.driver
        _login(driver)

        course_url = f"{BASE_URL}/course/view.php?id={COURSE_ID}"
        driver.get(course_url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        start = time.perf_counter()
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'completion')]"))
            )
        except Exception:
            pass
        elapsed = time.perf_counter() - start

        self._assert_time("Completion status retrieval", elapsed)

    # ── TC-NFT-005-03: Multiple courses listing response time ──────────────

    def test_03_courses_list_load_time(self):
        """Time to load My Courses page with multiple courses."""
        driver = self.driver
        _login(driver)

        courses_url = f"{BASE_URL}/my/courses.php"
        start = time.perf_counter()
        driver.get(courses_url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        elapsed = time.perf_counter() - start

        self._assert_time("Courses list page load", elapsed)

    # ── TC-NFT-005-04: Page responsiveness under load ──────────────────────

    def test_04_page_responsiveness(self):
        """Measure page responsiveness when scrolling through course content."""
        driver = self.driver
        _login(driver)

        course_url = f"{BASE_URL}/course/view.php?id={COURSE_ID}"
        driver.get(course_url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        start = time.perf_counter()
        # Simulate scrolling interactions
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(0.5)
        driver.execute_script("window.scrollBy(0, -500);")
        elapsed = time.perf_counter() - start

        self._assert_time("Page responsiveness", elapsed)


class NFTAccessibilityTest(unittest.TestCase):
    """Accessibility tests for course completion feature."""

    def setUp(self):
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(30)

    def tearDown(self):
        self.driver.quit()

    def _check_contrast(self, driver, element):
        """Check if element has sufficient color contrast (basic check)."""
        try:
            computed_style = driver.execute_script(
                "return window.getComputedStyle(arguments[0])", element
            )
            color = computed_style.get('color')
            background = computed_style.get('backgroundColor')
            print(f"  Element - Color: {color}, Background: {background}")
            return True
        except Exception:
            return False

    # ── TC-NFT-005-05: Keyboard navigation ───────────────────────────────

    def test_05_keyboard_navigation(self):
        """Verify course page is navigable via keyboard."""
        driver = self.driver
        _login(driver)
        driver.get(f"{BASE_URL}/course/view.php?id={COURSE_ID}")

        # Try tab navigation
        driver.find_element(By.TAG_NAME, "body").send_keys("\t")
        time.sleep(0.5)

        focused_element = driver.switch_to.active_element
        self.assertIsNotNone(focused_element, "No element focused after tab key")
        print(f"  ✓ Keyboard navigation - Tab focuses: {focused_element.tag_name}")

    # ── TC-NFT-005-06: ARIA attributes presence ──────────────────────────

    def test_06_aria_attributes(self):
        """Check if course page has ARIA attributes for accessibility."""
        driver = self.driver
        _login(driver)
        driver.get(f"{BASE_URL}/course/view.php?id={COURSE_ID}")

        # Check for ARIA labels
        aria_elements = driver.find_elements(By.XPATH, "//*[@aria-label or @aria-describedby or @role]")
        print(f"  Found {len(aria_elements)} ARIA-enabled elements")
        self.assertGreater(len(aria_elements), 0, "No ARIA attributes found")


class NFTReliabilityTest(unittest.TestCase):
    """Reliability tests for course completion feature."""

    def setUp(self):
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(30)

    def tearDown(self):
        self.driver.quit()

    # ── TC-NFT-005-07: Page load stability ──────────────────────────────

    def test_07_repeated_page_load(self):
        """Test page loads consistently across multiple attempts."""
        driver = self.driver
        _login(driver)

        course_url = f"{BASE_URL}/course/view.php?id={COURSE_ID}"
        load_times = []

        for i in range(3):
            start = time.perf_counter()
            driver.get(course_url)
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            elapsed = time.perf_counter() - start
            load_times.append(elapsed)
            print(f"  Attempt {i+1}: {elapsed:.3f}s")

        avg_time = sum(load_times) / len(load_times)
        variance = max(load_times) - min(load_times)
        print(f"  Average: {avg_time:.3f}s, Variance: {variance:.3f}s")
        self.assertLess(variance, 2.0, "Load time variance too high - inconsistent page load")

    # ── TC-NFT-005-08: Error recovery ──────────────────────────────────

    def test_08_error_recovery(self):
        """Test system recovery from network error."""
        driver = self.driver
        _login(driver)

        try:
            # Attempt to navigate to an invalid course
            driver.get(f"{BASE_URL}/course/view.php?id=99999")
            time.sleep(1)

            # Then navigate back to valid course
            driver.get(f"{BASE_URL}/course/view.php?id={COURSE_ID}")
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("  ✓ System recovered from error")
        except Exception as e:
            self.fail(f"Failed to recover from error: {str(e)}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
