import csv
import time
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


LOGIN_URL = "https://school.moodledemo.net/login/index.php"
COURSE_URL = "https://school.moodledemo.net/course/view.php?id=71"
QUIZ_NAME = "AAA"
USERNAME = "student"
PASSWORD = "moodle26"


def load_test_data(file_path="data/ecp_data.csv"):
    with open(file_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class QuizNumericalECP(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.driver = webdriver.Chrome()
        cls.driver.maximize_window()
        cls.wait = WebDriverWait(cls.driver, 60)
        cls.login()

    @classmethod
    def click_js(cls, element):
        cls.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});",
            element
        )
        time.sleep(0.3)
        cls.driver.execute_script("arguments[0].click();", element)
        time.sleep(0.5)

    @classmethod
    def login(cls):
        driver = cls.driver
        wait = cls.wait

        for attempt in range(3):
            try:
                driver.get(LOGIN_URL)

                wait.until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )

                username_box = wait.until(
                    EC.presence_of_element_located((By.ID, "username"))
                )
                password_box = wait.until(
                    EC.presence_of_element_located((By.ID, "password"))
                )

                driver.execute_script(
                    """
                    arguments[0].value = arguments[2];
                    arguments[1].value = arguments[3];

                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[1].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                    arguments[1].dispatchEvent(new Event('change', { bubbles: true }));
                    """,
                    username_box,
                    password_box,
                    USERNAME,
                    PASSWORD,
                )

                login_btn = wait.until(
                    EC.presence_of_element_located((By.ID, "loginbtn"))
                )
                cls.click_js(login_btn)

                time.sleep(2)
                print("Login student OK")
                return

            except Exception as e:
                print(f"Login retry {attempt + 1}/3: {type(e).__name__}")
                time.sleep(1)

        raise Exception("Student login failed after 3 retries")

    def _get_page_text(self):
        return self.driver.page_source.lower()

    def _start_attempt(self):
        driver = self.driver
        wait = self.wait

        driver.get(COURSE_URL)
        time.sleep(2)

        quiz_link = wait.until(
            EC.presence_of_element_located((By.LINK_TEXT, QUIZ_NAME))
        )
        self.click_js(quiz_link)

        time.sleep(2)

        attempt_btn = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//button[contains(.,'ttempt quiz')]")
            )
        )
        self.click_js(attempt_btn)

        # Có lúc Moodle hiện nút Start attempt / id_submitbutton
        try:
            start_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "id_submitbutton"))
            )
            self.click_js(start_btn)
        except TimeoutException:
            pass

        time.sleep(2)

    def _enter_answer_and_next(self, value):
        wait = self.wait

        input_box = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//span[contains(@class,'answer')]/input")
            )
        )

        input_box.click()
        input_box.clear()

        value = "" if value is None else str(value)

        if value.strip() != "":
            input_box.send_keys(value)

        time.sleep(1)

        next_btn = wait.until(
            EC.presence_of_element_located((By.ID, "mod_quiz-next-nav"))
        )
        self.click_js(next_btn)

        time.sleep(2)

    def _is_summary_page(self):
        page_text = self._get_page_text()

        if "summary of attempt" in page_text:
            return True

        buttons = self.driver.find_elements(
            By.XPATH,
            "//button[contains(normalize-space(.),'Submit all and finish')]"
        )

        return len(buttons) > 0

    def _return_to_attempt_if_available(self):
        buttons = self.driver.find_elements(
            By.XPATH,
            "//button[contains(normalize-space(.),'Return to attempt')]"
            " | //a[contains(normalize-space(.),'Return to attempt')]"
        )

        if buttons:
            self.click_js(buttons[0])
            time.sleep(2)
            return True

        return False

    def _go_to_summary_page(self):
        """
        Dùng sau khi verify invalid input.
        Từ trang question quay lại Summary để submit bài.
        """
        for _ in range(3):
            if self._is_summary_page():
                return

            next_buttons = self.driver.find_elements(By.ID, "mod_quiz-next-nav")

            if next_buttons:
                self.click_js(next_buttons[0])
                time.sleep(2)
                continue

            finish_links = self.driver.find_elements(By.LINK_TEXT, "Finish attempt ...")

            if finish_links:
                self.click_js(finish_links[0])
                time.sleep(2)
                continue

            break

    def _submit_from_summary(self):
        """
        Flow record:
        Summary page
        → Submit all and finish
        → form frm-finishattempt button
        → confirm button data-action=save
        """

        self._go_to_summary_page()

        submit_summary_btn = self.wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//button[contains(normalize-space(.),'Submit all and finish')]"
                )
            )
        )
        self.click_js(submit_summary_btn)

        time.sleep(1)

        # Trang confirm có form frm-finishattempt
        try:
            submit_form_btn = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//form[@id='frm-finishattempt']/button")
                )
            )
            self.click_js(submit_form_btn)
        except TimeoutException:
            pass

        time.sleep(1)

        # Modal confirm cuối
        try:
            confirm_btn = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[@data-action='save']")
                )
            )
            self.click_js(confirm_btn)
        except TimeoutException:
            pass

        time.sleep(2)

    def run_ecp_case(self, row):
        test_id = row["test_id"]
        input_value = row["input_value"]
        expected = row["expected_result"].lower().strip()

        print(f"\nRunning {test_id} | input='{input_value}' | expected='{expected}'")

        # 1. Student vào làm quiz
        self._start_attempt()

        # 2. Nhập answer và bấm Next page
        self._enter_answer_and_next(input_value)

        # 3. Case invalid:
        # Sau khi Next, Summary thường hiện "Incomplete answer".
        # Cần bấm Return to attempt để thấy lỗi "You must enter a valid number."
        if "valid number" in expected:
            summary_text = self._get_page_text()

            self.assertIn(
                "incomplete answer",
                summary_text,
                f"[FAIL] {test_id}: Expected 'Incomplete answer' on summary page"
            )

            returned = self._return_to_attempt_if_available()

            self.assertTrue(
                returned,
                f"[FAIL] {test_id}: Cannot find Return to attempt button"
            )

            page_text = self._get_page_text()

            self.assertIn(
                expected,
                page_text,
                f"[FAIL] {test_id}: Expected '{expected}'"
            )

        # 4. Case valid hoặc empty:
        # Verify trực tiếp ở Summary of attempt
        else:
            page_text = self._get_page_text()

            self.assertIn(
                expected,
                page_text,
                f"[FAIL] {test_id}: Expected '{expected}'"
            )

        print(f"[PASS] {test_id}")

        # 5. Submit bài để testcase sau có thể attempt mới
        self._submit_from_summary()

    @classmethod
    def tearDownClass(cls):
        time.sleep(1)
        try:
            cls.driver.quit()
        except Exception:
            pass


def make_test(row):
    def test(self):
        self.run_ecp_case(row)
    return test


test_data = load_test_data("data/ecp_data.csv")

for row in test_data:
    test_name = f"test_{row['test_id'].replace('-', '_')}"
    setattr(QuizNumericalECP, test_name, make_test(row))


if __name__ == "__main__":
    unittest.main(verbosity=2)