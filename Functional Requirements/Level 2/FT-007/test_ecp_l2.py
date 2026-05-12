import csv
import time
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


BY_MAP = {
    "id": By.ID,
    "xpath": By.XPATH,
    "css": By.CSS_SELECTOR,
    "name": By.NAME,
    "link": By.LINK_TEXT,
}


def load_test_data(file_path="data/ecp_l2_data.csv"):
    with open(file_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class QuizNumericalECPLevel2(unittest.TestCase):

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
        time.sleep(0.3)
        cls.driver.execute_script("arguments[0].click();", element)
        time.sleep(0.5)

    def login(self, login_url, username, password):
        driver = self.driver
        wait = self.wait

        for attempt in range(3):
            try:
                driver.get(login_url)

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
                    username,
                    password,
                )

                login_btn = wait.until(
                    EC.presence_of_element_located((By.ID, "loginbtn"))
                )
                self.click_js(login_btn)

                time.sleep(2)
                print("Login student OK")
                return

            except Exception as e:
                print(f"Login retry {attempt + 1}/3: {type(e).__name__}")
                time.sleep(1)

        raise Exception("Student login failed after 3 retries")

    def logout_if_needed(self, user_menu_id, logout_link_text):
        try:
            user_menu = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, user_menu_id))
            )
            self.click_js(user_menu)

            logout_link = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.LINK_TEXT, logout_link_text))
            )
            self.click_js(logout_link)

            time.sleep(2)
        except Exception:
            pass

    def get_page_text(self):
        return self.driver.page_source.lower()

    def start_attempt(self, row):
        driver = self.driver
        wait = self.wait

        course_url = row["course_url"]
        quiz_name = row["quiz_name"]
        attempt_button_xpath = row["attempt_button_xpath"]
        start_button_id = row["start_button_id"]

        driver.get(course_url)

        wait.until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        time.sleep(2)

        # Tìm quiz AAA theo link Moodle quiz.
        # Nếu có nhiều quiz AAA thì lấy cái cuối cùng, thường là quiz mới tạo gần nhất.
        quiz_links = wait.until(
            EC.presence_of_all_elements_located(
                (
                    By.XPATH,
                    f"//a[contains(@href,'/mod/quiz/view.php') and normalize-space()='{quiz_name}']"
                )
            )
        )

        quiz_link = quiz_links[-1]

        self.click_js(quiz_link)
        time.sleep(2)

        attempt_btn = wait.until(
            EC.presence_of_element_located((By.XPATH, attempt_button_xpath))
        )
        self.click_js(attempt_btn)

        try:
            start_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, start_button_id))
            )
            self.click_js(start_btn)
        except TimeoutException:
            pass

        time.sleep(2)

    def enter_answer_and_next(self, row):
        wait = self.wait

        locator_type = row["answer_locator_type"].lower().strip()
        locator_value = row["answer_locator_value"]
        input_value = row["input_value"]
        next_button_id = row["next_button_id"]

        by = BY_MAP.get(locator_type)

        if by is None:
            raise ValueError(f"Unsupported locator type: {locator_type}")

        input_box = wait.until(
            EC.presence_of_element_located((by, locator_value))
        )

        input_box.click()
        input_box.clear()

        value = "" if input_value is None else str(input_value)

        if value.strip() != "":
            input_box.send_keys(value)

        time.sleep(1)

        next_btn = wait.until(
            EC.presence_of_element_located((By.ID, next_button_id))
        )
        self.click_js(next_btn)

        time.sleep(2)

    def is_summary_page(self, row):
        page_text = self.get_page_text()

        if "summary of attempt" in page_text:
            return True

        submit_xpath = row["submit_button_xpath"]

        buttons = self.driver.find_elements(By.XPATH, submit_xpath)

        return len(buttons) > 0

    def return_to_attempt_if_available(self, row):
        return_button_xpath = row["return_button_xpath"]

        buttons = self.driver.find_elements(By.XPATH, return_button_xpath)

        if buttons:
            self.click_js(buttons[0])
            time.sleep(2)
            return True

        return False

    def go_to_summary_page(self, row):
        """
        Dùng sau khi verify invalid input.
        Từ trang question quay lại Summary để submit bài.
        """
        next_button_id = row["next_button_id"]
        finish_link_text = row["finish_link_text"]

        for _ in range(3):
            if self.is_summary_page(row):
                return

            next_buttons = self.driver.find_elements(By.ID, next_button_id)

            if next_buttons:
                self.click_js(next_buttons[0])
                time.sleep(2)
                continue

            finish_links = self.driver.find_elements(By.LINK_TEXT, finish_link_text)

            if finish_links:
                self.click_js(finish_links[0])
                time.sleep(2)
                continue

            break

    def submit_from_summary(self, row):
        """
        Summary page
        → Submit all and finish
        → confirm form nếu có
        → confirm modal nếu có
        """

        self.go_to_summary_page(row)

        submit_xpath = row["submit_button_xpath"]
        confirm_form_xpath = row["confirm_form_xpath"]
        confirm_button_xpath = row["confirm_button_xpath"]

        submit_summary_btn = self.wait.until(
            EC.presence_of_element_located((By.XPATH, submit_xpath))
        )
        self.click_js(submit_summary_btn)

        time.sleep(1)

        try:
            submit_form_btn = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, confirm_form_xpath))
            )
            self.click_js(submit_form_btn)
        except TimeoutException:
            pass

        time.sleep(1)

        try:
            confirm_btn = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, confirm_button_xpath))
            )
            self.click_js(confirm_btn)
        except TimeoutException:
            pass

        time.sleep(2)

    def run_ecp_l2_case(self, row):
        test_id = row["test_id"]
        expected = row["expected_result"].lower().strip()

        print(
            f"\nRunning {test_id} | input='{row['input_value']}' | expected='{expected}'"
        )

        self.login(
            row["login_url"],
            row["username"],
            row["password"]
        )

        self.start_attempt(row)

        self.enter_answer_and_next(row)

        if "valid number" in expected:
            summary_text = self.get_page_text()

            self.assertIn(
                "incomplete answer",
                summary_text,
                f"[FAIL] {test_id}: Expected 'Incomplete answer' on summary page"
            )

            returned = self.return_to_attempt_if_available(row)

            self.assertTrue(
                returned,
                f"[FAIL] {test_id}: Cannot find Return to attempt button"
            )

            page_text = self.get_page_text()

            self.assertIn(
                expected,
                page_text,
                f"[FAIL] {test_id}: Expected '{expected}'"
            )

        else:
            page_text = self.get_page_text()

            self.assertIn(
                expected,
                page_text,
                f"[FAIL] {test_id}: Expected '{expected}'"
            )

        print(f"[PASS] {test_id}")

        self.submit_from_summary(row)

        self.logout_if_needed(
            row["user_menu_id"],
            row["logout_link_text"]
        )

    @classmethod
    def tearDownClass(cls):
        time.sleep(1)
        try:
            cls.driver.quit()
        except Exception:
            pass


def make_test(row):
    def test(self):
        self.run_ecp_l2_case(row)

    return test


test_data = load_test_data("data/ecp_l2_data.csv")

for row in test_data:
    test_name = f"test_{row['test_id'].replace('-', '_')}"
    setattr(QuizNumericalECPLevel2, test_name, make_test(row))


if __name__ == "__main__":
    unittest.main(verbosity=2)