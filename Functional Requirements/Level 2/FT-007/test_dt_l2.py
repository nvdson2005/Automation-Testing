import csv
import time
import unittest
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


DATA_FILE = Path(__file__).resolve().parent / "data" / "dt_l2_data.csv"


def load_test_data(file_path=DATA_FILE):
    with open(file_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class DecisionTableLevel2(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.driver = webdriver.Chrome()
        cls.driver.maximize_window()
        cls.wait = WebDriverWait(cls.driver, 60)

    @classmethod
    def click_js(cls, element):
        cls.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});",
            element
        )
        time.sleep(0.2)
        cls.driver.execute_script("arguments[0].click();", element)
        time.sleep(0.4)

    def login(self, row):
        driver = self.driver

        login_url = row["login_url"]
        username = row["username"]
        password = row["password"]

        for attempt in range(3):
            try:
                driver.get(login_url)

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
                    username,
                    password,
                )

                WebDriverWait(driver, 10).until(
                    lambda d: (
                        "login" not in d.current_url
                        or len(d.find_elements(By.ID, row["user_menu_id"])) > 0
                    )
                )

                print(f"Login OK: {username}")
                return

            except Exception as e:
                print(f"Login retry {attempt + 1}/3: {type(e).__name__}")
                time.sleep(0.5)

        raise Exception(f"Login failed after 3 retries: {username}")

    def logout_if_needed(self, row):
        try:
            user_menu = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, row["user_menu_id"]))
            )
            self.click_js(user_menu)

            logout_link = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.LINK_TEXT, row["logout_link_text"]))
            )
            self.click_js(logout_link)
            time.sleep(1)
        except Exception:
            pass

    def get_page_text(self):
        return self.driver.page_source.lower()

    def is_summary_page(self, row):
        page_text = self.get_page_text()

        if "summary of attempt" in page_text:
            return True

        submit_buttons = self.driver.find_elements(By.XPATH, row["submit_button_xpath"])
        return len(submit_buttons) > 0

    def start_attempt(self, row):
        driver = self.driver
        wait = self.wait

        driver.get(row["quiz_url"])

        wait.until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        time.sleep(1)

        if "guests cannot see or attempt quizzes" in driver.page_source.lower():
            raise Exception("Student is not logged in. Moodle opened quiz as guest.")

        attempt_btn = wait.until(
            EC.presence_of_element_located((By.XPATH, row["attempt_button_xpath"]))
        )
        self.click_js(attempt_btn)

        try:
            start_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, row["start_button_id"]))
            )
            self.click_js(start_btn)
        except TimeoutException:
            pass

        time.sleep(1)

    def answer_first_choice_on_page(self, row, remaining_to_answer):
        if remaining_to_answer <= 0:
            return 0

        answered = 0
        question_blocks = self.driver.find_elements(By.CSS_SELECTOR, row["question_block_css"])

        for block in question_blocks:
            if answered >= remaining_to_answer:
                break

            try:
                options = block.find_elements(By.CSS_SELECTOR, row["answer_option_css"])
                clickable_options = [
                    option for option in options
                    if option.is_enabled() and option.get_attribute("disabled") is None
                ]

                if clickable_options:
                    self.click_js(clickable_options[0])
                    answered += 1
            except Exception:
                pass

        return answered

    def go_to_summary_after_answering(self, row):
        answers_to_fill = int(row["answers_to_fill"])
        total_answered = 0

        for _ in range(15):
            if self.is_summary_page(row):
                return total_answered

            remaining = max(0, answers_to_fill - total_answered)
            total_answered += self.answer_first_choice_on_page(row, remaining)

            time.sleep(0.3)

            if self.is_summary_page(row):
                return total_answered

            next_buttons = self.driver.find_elements(By.ID, row["next_button_id"])
            if next_buttons:
                self.click_js(next_buttons[0])
                time.sleep(0.7)
                continue

            finish_links = self.driver.find_elements(By.LINK_TEXT, row["finish_link_text"])
            if finish_links:
                self.click_js(finish_links[0])
                time.sleep(0.7)
                continue

            break

        return total_answered

    def submit_attempt(self, row):
        driver = self.driver

        if not self.is_summary_page(row):
            for _ in range(3):
                next_buttons = driver.find_elements(By.ID, row["next_button_id"])
                if next_buttons:
                    self.click_js(next_buttons[0])
                    time.sleep(0.7)
                    if self.is_summary_page(row):
                        break
                    continue

                finish_links = driver.find_elements(By.LINK_TEXT, row["finish_link_text"])
                if finish_links:
                    self.click_js(finish_links[0])
                    time.sleep(0.7)
                    if self.is_summary_page(row):
                        break
                    continue

                break

        submit_btn = self.wait.until(
            EC.presence_of_element_located((By.XPATH, row["submit_button_xpath"]))
        )
        self.click_js(submit_btn)

        time.sleep(0.7)

        try:
            confirm_form_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, row["confirm_form_xpath"]))
            )
            self.click_js(confirm_form_btn)
            time.sleep(0.7)
        except TimeoutException:
            pass

        try:
            confirm_modal_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, row["confirm_button_xpath"]))
            )
            self.click_js(confirm_modal_btn)
        except TimeoutException:
            pass

        time.sleep(1)

    def verify_final_finished(self, row, test_id):
        self.driver.get(row["quiz_url"])
        time.sleep(2)

        page_text = self.get_page_text()
        expected_final = row["expected_final"].lower().strip()

        self.assertIn(
            expected_final,
            page_text,
            f"[FAIL] {test_id}: Expected final quiz status '{expected_final}'."
        )

    def run_dt_l2_case(self, row):
        test_id = row["test_id"]
        answer_state = row["answer_state"]
        expected_summary = row["expected_summary"].lower().strip()

        print(
            f"\nRunning {test_id} | rule={row['rule']} | state={answer_state} "
            f"| answers_to_fill={row['answers_to_fill']} | expected_summary={expected_summary}"
        )

        self.login(row)
        self.start_attempt(row)

        answered_count = self.go_to_summary_after_answering(row)
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

        self.submit_attempt(row)
        self.verify_final_finished(row, test_id)

        print(f"[PASS] {test_id}")
        self.logout_if_needed(row)

    @classmethod
    def tearDownClass(cls):
        time.sleep(1)
        try:
            cls.driver.quit()
        except Exception:
            pass


def make_test(row):
    def test(self):
        self.run_dt_l2_case(row)

    return test


test_data = load_test_data()

for row in test_data:
    test_name = f"test_{row['test_id'].replace('-', '_')}"
    setattr(DecisionTableLevel2, test_name, make_test(row))


if __name__ == "__main__":
    unittest.main(verbosity=2)
