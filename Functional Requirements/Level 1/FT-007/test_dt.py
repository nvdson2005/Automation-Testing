import csv
import time
import unittest
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


LOGIN_URL = "https://school.moodledemo.net/login/index.php"
QUIZ_URL = "https://school.moodledemo.net/mod/quiz/view.php?id=1150"

STUDENT_USER = "student"
STUDENT_PASS = "moodle26"

DATA_FILE = Path(__file__).resolve().parent / "data" / "dt_data.csv"


def load_test_data(file_path=DATA_FILE):
    with open(file_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class DecisionTableQuizSubmission(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.driver = webdriver.Chrome()
        cls.driver.maximize_window()
        cls.wait = WebDriverWait(cls.driver, 60)
        cls.login_student()

    @classmethod
    def click_js(cls, element):
        cls.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});",
            element
        )
        time.sleep(0.2)
        cls.driver.execute_script("arguments[0].click();", element)
        time.sleep(0.4)

    @classmethod
    def login_student(cls):
        driver = cls.driver

        for attempt in range(3):
            try:
                driver.get(LOGIN_URL)
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script(
                        "return !!document.getElementById('username') "
                        "&& !!document.getElementById('password') "
                        "&& !!document.getElementById('loginbtn');"
                    )
                )

                driver.execute_script(
                    """
                    const usernameBox = document.getElementById('username');
                    const passwordBox = document.getElementById('password');
                    const loginBtn = document.getElementById('loginbtn');

                    usernameBox.value = arguments[0];
                    passwordBox.value = arguments[1];

                    usernameBox.dispatchEvent(new Event('input', { bubbles: true }));
                    passwordBox.dispatchEvent(new Event('input', { bubbles: true }));
                    usernameBox.dispatchEvent(new Event('change', { bubbles: true }));
                    passwordBox.dispatchEvent(new Event('change', { bubbles: true }));

                    loginBtn.click();
                    """,
                    STUDENT_USER,
                    STUDENT_PASS,
                )

                WebDriverWait(driver, 10).until(
                    lambda d: (
                        "login" not in d.current_url
                        or len(d.find_elements(By.ID, "user-menu-toggle")) > 0
                    )
                )

                print("Login student OK")
                return

            except Exception as e:
                print(f"Login retry {attempt + 1}/3: {type(e).__name__}")
                time.sleep(0.5)

        raise Exception("Student login failed after 3 retries")

    def get_page_text(self):
        return self.driver.page_source.lower()

    def is_summary_page(self):
        text = self.get_page_text()
        if "summary of attempt" in text:
            return True

        return len(
            self.driver.find_elements(
                By.XPATH,
                "//button[contains(normalize-space(.),'Submit all and finish')]"
            )
        ) > 0

    def start_attempt(self):
        driver = self.driver
        wait = self.wait

        driver.get(QUIZ_URL)
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(1)

        if "guests cannot see or attempt quizzes" in driver.page_source.lower():
            raise Exception("Student is not logged in. Moodle opened quiz as guest.")

        attempt_btn = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//button[contains(.,'ttempt quiz') or contains(.,'Continue your attempt')]"
                )
            )
        )
        self.click_js(attempt_btn)

        try:
            start_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "id_submitbutton"))
            )
            self.click_js(start_btn)
        except TimeoutException:
            pass

        time.sleep(1)

    def answer_first_choice_on_page(self, remaining_to_answer):
        if remaining_to_answer <= 0:
            return 0

        answered = 0
        question_blocks = self.driver.find_elements(By.CSS_SELECTOR, "div.que")

        for block in question_blocks:
            if answered >= remaining_to_answer:
                break

            try:
                radios = block.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                clickable_radios = [
                    radio for radio in radios
                    if radio.is_enabled() and radio.get_attribute("disabled") is None
                ]

                if clickable_radios:
                    self.click_js(clickable_radios[0])
                    answered += 1
            except Exception:
                pass

        return answered

    def go_to_summary_after_answering(self, answers_to_fill):
        total_answered = 0

        for _ in range(15):
            if self.is_summary_page():
                return total_answered

            remaining = max(0, answers_to_fill - total_answered)
            total_answered += self.answer_first_choice_on_page(remaining)

            time.sleep(0.2)

            if self.is_summary_page():
                return total_answered

            next_buttons = self.driver.find_elements(By.ID, "mod_quiz-next-nav")
            if next_buttons:
                self.click_js(next_buttons[0])
                time.sleep(0.5)
                continue

            finish_links = self.driver.find_elements(By.LINK_TEXT, "Finish attempt ...")
            if finish_links:
                self.click_js(finish_links[0])
                time.sleep(1)
                continue

            break

        return total_answered

    def submit_attempt(self):
        driver = self.driver

        if not self.is_summary_page():
            for _ in range(3):
                next_buttons = driver.find_elements(By.ID, "mod_quiz-next-nav")
                if next_buttons:
                    self.click_js(next_buttons[0])
                    time.sleep(1)
                    if self.is_summary_page():
                        break
                    continue

                finish_links = driver.find_elements(By.LINK_TEXT, "Finish attempt ...")
                if finish_links:
                    self.click_js(finish_links[0])
                    time.sleep(1)
                    if self.is_summary_page():
                        break
                    continue

                break

        submit_btn = self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//button[contains(normalize-space(.),'Submit all and finish')]")
            )
        )
        self.click_js(submit_btn)
        time.sleep(1)

        try:
            confirm_form_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//form[@id='frm-finishattempt']/button")
                )
            )
            self.click_js(confirm_form_btn)
            time.sleep(1)
        except TimeoutException:
            pass

        try:
            confirm_modal_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[@data-action='save']")
                )
            )
            self.click_js(confirm_modal_btn)
        except TimeoutException:
            pass

        time.sleep(1)

    def verify_final_finished(self, test_id):
        self.driver.get(QUIZ_URL)
        time.sleep(2)

        page_text = self.get_page_text()

        self.assertIn(
            "finished",
            page_text,
            f"[FAIL] {test_id}: Expected final quiz status 'Finished'."
        )

    def run_dt_case(self, row):
        test_id = row["test_id"]
        answer_state = row["answer_state"]
        answers_to_fill = int(row["answers_to_fill"])
        expected_summary = row["expected_summary"].lower().strip()
        expected_final = row["expected_final"].lower().strip()

        print(
            f"\nRunning {test_id} | state={answer_state} "
            f"| answers_to_fill={answers_to_fill} | expected_summary={expected_summary}"
        )

        self.start_attempt()

        answered_count = self.go_to_summary_after_answering(answers_to_fill)
        print(f"Answered count: {answered_count}")

        summary_text = self.get_page_text()

        if answer_state == "all":
            self.assertIn(
                expected_summary,
                summary_text,
                f"[FAIL] {test_id}: Expected '{expected_summary}' on Summary page."
            )
            self.assertNotIn(
                "not answered",
                summary_text,
                f"[FAIL] {test_id}: All questions should be answered, but 'Not answered' appeared."
            )
            self.assertNotIn(
                "not yet answered",
                summary_text,
                f"[FAIL] {test_id}: All questions should be answered, but 'Not yet answered' appeared."
            )
        else:
            self.assertTrue(
                "not answered" in summary_text or "not yet answered" in summary_text,
                f"[FAIL] {test_id}: Expected unanswered warning on Summary page."
            )

        self.submit_attempt()

        if expected_final == "finished":
            self.verify_final_finished(test_id)

        print(f"[PASS] {test_id}")

    @classmethod
    def tearDownClass(cls):
        time.sleep(1)
        try:
            cls.driver.quit()
        except Exception:
            pass


def make_test(row):
    def test(self):
        self.run_dt_case(row)

    return test


test_data = load_test_data()

for row in test_data:
    test_name = f"test_{row['test_id'].replace('-', '_')}"
    setattr(DecisionTableQuizSubmission, test_name, make_test(row))


if __name__ == "__main__":
    unittest.main(verbosity=2)
