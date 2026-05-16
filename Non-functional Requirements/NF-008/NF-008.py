# =============================================================
# Project #3 – Non-Functional Testing
# Type     : Performance Testing (Response Time Client-side)
# Features : FT008 – Add New User  |  FT009 – Add New Course
# Tool     : Selenium WebDriver + Python time module
# Run      : python NF-008.py
# =============================================================

import statistics
import time
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# ── Config ────────────────────────────────────────────────────
SITE_URL        = "https://school.moodledemo.net/"
ADD_USER_URL    = "https://school.moodledemo.net/user/editadvanced.php?id=-1"
ADD_COURSE_URL  = "https://school.moodledemo.net/course/edit.php?category=0"
ADMIN_USER      = "manager"
ADMIN_PASS      = "moodle26" # Đã sửa mật khẩu đúng
WAIT_SEC        = 20
REPEAT          = 5          # Số lần chạy cho mỗi NFR
THRESHOLD_SEC   = 5.0        # Ngưỡng chấp nhận (giây)

# ── Reusable users for NFR-1 ──────────────────────────────────
NFR1_USERS = [
    {"firstname": "Perf", "lastname": "Test1"},
    {"firstname": "Perf", "lastname": "Test2"},
    {"firstname": "Perf", "lastname": "Test3"},
    {"firstname": "Perf", "lastname": "Test4"},
    {"firstname": "Perf", "lastname": "Test5"},
]

# ── Reusable course names for NFR-2 ───────────────────────────
NFR2_COURSES = [
    {"fullname": "PerfCourse1"},
    {"fullname": "PerfCourse2"},
    {"fullname": "PerfCourse3"},
    {"fullname": "PerfCourse4"},
    {"fullname": "PerfCourse5"},
]


# ─────────────────────────────────────────────────────────────
class NonFunctionalPerformanceTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        opts = Options()
        opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        cls.driver = webdriver.Chrome(options=opts)
        cls.driver.maximize_window()
        cls.wait = WebDriverWait(cls.driver, WAIT_SEC)
        cls._login()

    @classmethod
    def _login(cls):
        """Log in once, reuse session for all tests."""
        cls.driver.get(SITE_URL)
        
        cls.wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "span.login a"))).click()
        
        time.sleep(1.5)
        
        try:
            uname_field = cls.wait.until(EC.element_to_be_clickable((By.ID, "username")))
            uname_field.clear()
            uname_field.send_keys(ADMIN_USER)
        except Exception:
            pass

        pwd = cls.wait.until(EC.presence_of_element_located((By.ID, "password")))
        pwd.clear()
        pwd.send_keys(ADMIN_PASS)
        
        cls.driver.find_element(By.ID, "login").submit()
        cls.wait.until(EC.url_contains("moodledemo.net"))
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    @staticmethod
    def _report(nfr_id, label, times, threshold):
        avg  = statistics.mean(times)
        mn   = min(times)
        mx   = max(times)
        passed = sum(1 for t in times if t <= threshold)
        sep = "=" * 65
        print(f"\n{sep}")
        print(f"{nfr_id}  {label}")
        print(f"  Ngưỡng (Threshold) : {threshold} s")
        print(f"  Số lần chạy        : {len(times)}")
        print(sep)
        for i, t in enumerate(times, 1):
            icon = "✔" if t <= threshold else "✘"
            print(f"  Run {i:02d}: {t:.3f}s  {icon}")
        print(f"{sep}")
        print(f"  Min = {mn:.3f}s | Max = {mx:.3f}s | Avg = {avg:.3f}s")
        verdict = "PASS ✔" if avg <= threshold else "FAIL ✘"
        print(f"  Đánh giá: {verdict}  ({passed}/{len(times)} requests đạt ngưỡng)")
        print(sep)
        return avg

    # ─────────────────────────────────────────────────────────
    # NFR-1 : Add New User – form submission response time
    # ─────────────────────────────────────────────────────────
    def test_NFR1_add_user_response_time(self):
        """
        NFR-1: Thời gian Submit form thêm User mới và hiển thị kết quả
        phải <= 5 giây cho mỗi thao tác.
        """
        driver, wait = self.driver, self.wait
        times = []

        for i, user in enumerate(NFR1_USERS[:REPEAT], 1):
            unique_user = f"nfr1user{int(time.time())}{i}"
            unique_email = f"nfr{i}{int(time.time())}@test.com"

            driver.get(ADD_USER_URL)
            wait.until(EC.presence_of_element_located((By.ID, "id_username")))

            # Fill form
            driver.find_element(By.ID, "id_username").send_keys(unique_user)
            driver.find_element(By.ID, "id_firstname").send_keys(user["firstname"])
            driver.find_element(By.ID, "id_lastname").send_keys(user["lastname"])
            driver.find_element(By.ID, "id_email").send_keys(unique_email)

            t_start = time.perf_counter()
            submit_btn = driver.find_element(By.ID, "id_submitbutton")
            driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
            time.sleep(0.2)
            driver.execute_script("arguments[0].click();", submit_btn)

            wait.until(EC.presence_of_element_located((
                By.XPATH,
                "//*[contains(@class,'alert-success') or "
                "contains(@id,'user-notifications') or "
                "contains(@class,'error') or "
                "contains(@id,'id_error_')]"
            )))
            elapsed = time.perf_counter() - t_start

            times.append(elapsed)
            print(f"  [NFR-1 Đang chạy] Run {i}: {elapsed:.3f}s | username={unique_user}")

        avg = self._report("NFR-1", "Add New User – form submission time", times, THRESHOLD_SEC)
        self.assertLessEqual(avg, THRESHOLD_SEC, f"[NFR-1] Average {avg:.3f}s exceeds threshold {THRESHOLD_SEC}s")

    # ─────────────────────────────────────────────────────────
    # NFR-2 : Add New Course – form submission response time
    # ─────────────────────────────────────────────────────────
    def test_NFR2_add_course_response_time(self):
        """
        NFR-2: Thời gian Submit form thêm Khóa học mới và hiển thị kết quả
        phải <= 5 giây cho mỗi thao tác.
        """
        driver, wait = self.driver, self.wait
        times = []

        for i, course in enumerate(NFR2_COURSES[:REPEAT], 1):
            unique_short = f"nfr2c{int(time.time())}{i}"

            driver.get(ADD_COURSE_URL)
            wait.until(EC.presence_of_element_located((By.ID, "id_fullname")))

            # Fill form
            fn = driver.find_element(By.ID, "id_fullname")
            fn.clear()
            fn.send_keys(course["fullname"])

            sn = driver.find_element(By.ID, "id_shortname")
            sn.clear()
            sn.send_keys(unique_short)

            try:
                btn = driver.find_elements(By.XPATH, "//span[contains(@class,'form-autocomplete-downarrow')]")
                if btn:
                    btn[0].click()
                    time.sleep(0.4)
                    inp = driver.find_element(By.XPATH, "//input[@id[contains(.,'form_autocomplete_input')]]")
                    inp.send_keys("LMS")
                    time.sleep(0.8)
                    opt = wait.until(EC.element_to_be_clickable((
                        By.XPATH, "//ul[contains(@class,'autocomplete-suggestions')]//li[1]"
                    )))
                    opt.click()
            except Exception:
                try:
                    Select(driver.find_element(By.ID, "id_category")).select_by_index(1)
                except Exception:
                    pass

            t_start = time.perf_counter()
            save_btn = driver.find_element(By.ID, "id_saveanddisplay")
            driver.execute_script("arguments[0].scrollIntoView(true);", save_btn)
            time.sleep(0.2)
            driver.execute_script("arguments[0].click();", save_btn)

            wait.until(EC.presence_of_element_located((
                By.XPATH,
                "//h1 | "
                "//*[contains(@id,'id_error_') or "
                "contains(@class,'error')]"
            )))
            elapsed = time.perf_counter() - t_start

            times.append(elapsed)
            print(f"  [NFR-2 Đang chạy] Run {i}: {elapsed:.3f}s | shortname={unique_short}")

        avg = self._report("NFR-2", "Add New Course – form submission time", times, THRESHOLD_SEC)
        self.assertLessEqual(avg, THRESHOLD_SEC, f"[NFR-2] Average {avg:.3f}s exceeds threshold {THRESHOLD_SEC}s")


if __name__ == "__main__":
    unittest.main(verbosity=2)