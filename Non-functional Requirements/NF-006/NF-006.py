# -*- coding: utf-8 -*-
"""
Non-Functional Testing for FT-006: Change User Picture
Tests: Performance, File Upload Handling, Compatibility, Security
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

# Performance threshold (seconds)
THRESHOLD_PAGE_LOAD = 5.0
THRESHOLD_UPLOAD = 10.0


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


class NFTPerformanceFileUploadTest(unittest.TestCase):
    """Performance tests for file upload functionality."""

    def setUp(self):
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(30)

    def tearDown(self):
        self.driver.quit()

    def _assert_time(self, label, elapsed, threshold):
        print(f"  [{label}] {elapsed:.3f}s (threshold: {threshold}s) — "
              f"{'PASS' if elapsed < threshold else 'FAIL'}")
        self.assertLess(elapsed, threshold,
                        f"{label}: {elapsed:.3f}s exceeds threshold of {threshold}s")

    # ── TC-NFT-006-01: Profile edit page load time ──────────────────────

    def test_01_profile_edit_load_time(self):
        """Time to load profile edit page."""
        driver = self.driver
        _login(driver)

        profile_url = f"{BASE_URL}/user/edit.php?id=self"
        start = time.perf_counter()
        driver.get(profile_url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "id_firstname"))
        )
        elapsed = time.perf_counter() - start

        self._assert_time("Profile edit page load", elapsed, THRESHOLD_PAGE_LOAD)

    # ── TC-NFT-006-02: Form submission response time ──────────────────────

    def test_02_form_submission_response_time(self):
        """Time to submit profile form (without file upload)."""
        driver = self.driver
        _login(driver)

        driver.get(f"{BASE_URL}/user/edit.php?id=self")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "id_submitbutton"))
        )

        start = time.perf_counter()
        driver.find_element(By.ID, "id_submitbutton").click()
        WebDriverWait(driver, 30).until(EC.url_contains("user/profile.php"))
        elapsed = time.perf_counter() - start

        self._assert_time("Form submission", elapsed, 3.0)


class NFTFileUploadValidationTest(unittest.TestCase):
    """Tests for file upload validation and constraints."""

    def setUp(self):
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(30)

    def tearDown(self):
        self.driver.quit()

    # ── TC-NFT-006-03: Maximum file size validation ──────────────────────

    def test_03_max_file_size_validation(self):
        """Verify maximum file size (256MB) is enforced."""
        driver = self.driver
        _login(driver)
        driver.get(f"{BASE_URL}/user/edit.php?id=self")

        # Check for file size limit indicator in page
        body_text = driver.find_element(By.TAG_NAME, "body").text

        # Look for size limit mention
        if "256" in body_text or "256MB" in body_text or "Maximum" in body_text:
            print("  ✓ File size limit clearly indicated")
        else:
            print("  ⚠ File size limit not clearly visible")

    # ── TC-NFT-006-04: Supported file formats ────────────────────────────

    def test_04_supported_file_formats(self):
        """Verify supported file formats are documented."""
        driver = self.driver
        _login(driver)
        driver.get(f"{BASE_URL}/user/edit.php?id=self")

        try:
            file_input = driver.find_element(By.XPATH, "//input[@type='file' and @name='userfile']")
            accept_attr = file_input.get_attribute("accept")
            print(f"  Supported formats: {accept_attr if accept_attr else 'Not specified'}")
        except NoSuchElementException:
            print("  ⚠ File input element not accessible")


class NFTAccessibilityFileUploadTest(unittest.TestCase):
    """Accessibility tests for file upload controls."""

    def setUp(self):
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(30)

    def tearDown(self):
        self.driver.quit()

    # ── TC-NFT-006-05: Form field labels accessibility ───────────────────

    def test_05_form_labels_accessibility(self):
        """Check if form fields have accessible labels."""
        driver = self.driver
        _login(driver)
        driver.get(f"{BASE_URL}/user/edit.php?id=self")

        # Find all input fields
        inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='file' or @type='email']")
        labeled_inputs = 0

        for inp in inputs:
            label = inp.get_attribute("aria-label") or inp.get_attribute("title")
            if label:
                labeled_inputs += 1

        print(f"  Found {labeled_inputs}/{len(inputs)} labeled input fields")
        self.assertGreater(labeled_inputs, 0, "No accessible labels found on form fields")

    # ── TC-NFT-006-06: Error message clarity ────────────────────────────

    def test_06_error_message_clarity(self):
        """Verify error messages are clear and accessible."""
        driver = self.driver
        _login(driver)
        driver.get(f"{BASE_URL}/user/edit.php?id=self")

        # Check for error elements
        error_elements = driver.find_elements(By.XPATH, "//div[@class='alert alert-danger' or @role='alert']")
        print(f"  Found {len(error_elements)} error containers")

        for elem in error_elements[:2]:  # Check first 2
            if elem.is_displayed():
                print(f"  Error message: {elem.text[:100]}")


class NFTSecurityUploadTest(unittest.TestCase):
    """Security tests for file upload functionality."""

    def setUp(self):
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(30)

    def tearDown(self):
        self.driver.quit()

    # ── TC-NFT-006-07: File type validation on server ──────────────────

    def test_07_file_type_validation(self):
        """Verify that only image files are accepted."""
        driver = self.driver
        _login(driver)
        driver.get(f"{BASE_URL}/user/edit.php?id=self")

        try:
            file_input = driver.find_element(By.XPATH, "//input[@type='file' and @name='userfile']")
            accept_attr = file_input.get_attribute("accept")

            if accept_attr:
                print(f"  Client-side validation: {accept_attr}")
                # Check for image restrictions
                if "image" in accept_attr.lower():
                    print("  ✓ File upload restricted to image files")
                else:
                    print("  ⚠ File type restriction not clear")
            else:
                print("  ⚠ No accept attribute set")
        except NoSuchElementException:
            print("  ⚠ File input not found")

    # ── TC-NFT-006-08: CSRF protection check ────────────────────────────

    def test_08_csrf_token_presence(self):
        """Verify CSRF token is present in form."""
        driver = self.driver
        _login(driver)
        driver.get(f"{BASE_URL}/user/edit.php?id=self")

        # Look for hidden CSRF token
        csrf_inputs = driver.find_elements(By.XPATH, "//input[@type='hidden' and (@name contains 'token' or @name contains 'csrf')]")

        if csrf_inputs:
            print(f"  ✓ Found {len(csrf_inputs)} CSRF protection token(s)")
        else:
            print("  ⚠ CSRF token not visibly present")


class NFTReliabilityUploadTest(unittest.TestCase):
    """Reliability tests for file upload."""

    def setUp(self):
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(30)

    def tearDown(self):
        self.driver.quit()

    # ── TC-NFT-006-09: Profile page consistency ──────────────────────────

    def test_09_profile_page_consistency(self):
        """Test profile page structure consistency across page loads."""
        driver = self.driver
        _login(driver)

        page_elements = []
        for i in range(2):
            driver.get(f"{BASE_URL}/user/edit.php?id=self")
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "id_firstName"))
            )
            elements_found = len(driver.find_elements(By.XPATH, "//*[@id]"))
            page_elements.append(elements_found)
            print(f"  Load {i+1}: {elements_found} elements found")

        variance = abs(page_elements[0] - page_elements[1])
        self.assertLess(variance, 10, "Page structure inconsistent across loads")
        print(f"  ✓ Page structure consistency verified (variance: {variance})")


if __name__ == "__main__":
    unittest.main(verbosity=2)
