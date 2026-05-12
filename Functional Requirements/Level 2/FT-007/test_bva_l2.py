import csv
import time
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


def load_test_data(file_path="data/bva_l2_data.csv"):
    with open(file_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class QuizAttemptsBVALevel2(unittest.TestCase):

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

    def login(self, login_url, username, password):
        driver = self.driver

        for attempt in range(3):
            try:
                driver.get(login_url)

                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )

                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script(
                        "return !!document.getElementById('username') && !!document.getElementById('password') && !!document.getElementById('loginbtn');"
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
                        or len(d.find_elements(By.ID, "user-menu-toggle")) > 0
                    )
                )

                print(f"    Login OK: {username}")
                return

            except Exception as e:
                print(f"    Login retry {attempt + 1}/3: {type(e).__name__}")
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

            time.sleep(1.5)
        except Exception:
            pass

    def reset_attempts(self, row):
        print("[CLEANUP] Reset quiz attempts")

        driver = self.driver
        wait = self.wait

        driver.get(row["report_url"])
        time.sleep(2)

        page_text = driver.page_source.lower()

        if (
            "no attempts have been made" in page_text
            or "nothing to display" in page_text
            or "no attempts" in page_text
        ):
            print("    No attempts found -> skip reset")
            return

        checkboxes = driver.find_elements(
            By.XPATH,
            "//input[@type='checkbox' and (contains(@name,'attemptid') or contains(@name,'attempt'))]"
        )

        if not checkboxes:
            print("    No attempt checkboxes found -> skip reset")
            return

        print(f"    Found {len(checkboxes)} attempt checkbox(es)")

        for checkbox in checkboxes:
            try:
                if checkbox.is_enabled() and not checkbox.is_selected():
                    self.click_js(checkbox)
            except Exception:
                pass

        try:
            delete_btn = wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//input[contains(@value,'Delete selected attempts')]"
                        " | //button[contains(.,'Delete selected attempts')]"
                    )
                )
            )
            self.click_js(delete_btn)
        except TimeoutException:
            print("    Delete selected attempts button not found -> skip reset")
            return

        try:
            confirm_btn = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//button[contains(.,'Yes')]"
                        " | //input[contains(@value,'Yes')]"
                        " | //button[contains(.,'Continue')]"
                        " | //input[contains(@value,'Continue')]"
                        " | //button[@data-action='save']"
                    )
                )
            )
            self.click_js(confirm_btn)
            print("    Attempts reset successfully")
        except TimeoutException:
            print("    Confirm button not found, maybe attempts were already deleted")

        time.sleep(1.5)

    def set_attempts_allowed(self, row):
        print(f"[PRE] Set attempts_allowed = {row['attempts_allowed']}")

        driver = self.driver
        wait = self.wait

        driver.get(row["quiz_url"])

        wait.until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        settings_tab = wait.until(
            EC.presence_of_element_located((By.XPATH, row["settings_tab_xpath"]))
        )
        self.click_js(settings_tab)

        wait.until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        expand_icons = driver.find_elements(By.XPATH, "//span[@title='Expand']")
        for icon in expand_icons:
            try:
                self.click_js(icon)
            except Exception:
                pass

        try:
            none_radio = driver.find_element(By.XPATH, "(//input[@type='radio'])[1]")
            self.click_js(none_radio)
        except Exception:
            pass

        attempts_dropdown = wait.until(
            EC.presence_of_element_located((By.ID, row["attempts_select_id"]))
        )

        attempts_allowed = str(row["attempts_allowed"]).strip()

        if attempts_allowed.lower() == "unlimited":
            value = "0"
        else:
            value = attempts_allowed

        driver.execute_script(
            """
            arguments[0].scrollIntoView({block:'center'});
            arguments[0].value = arguments[1];
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """,
            attempts_dropdown,
            value,
        )

        selected_value = attempts_dropdown.get_attribute("value")
        print("    Selected attempts =", selected_value)

        if selected_value != value:
            raise Exception(
                f"Failed to set attempts. Expected {value}, got {selected_value}"
            )

        save_btn = wait.until(
            EC.presence_of_element_located((By.ID, row["save_settings_button_id"]))
        )
        self.click_js(save_btn)

        wait.until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        time.sleep(1.5)

    def do_quiz_attempt_once(self, row, attempt_index, total_attempts):
        print(f"[PRE] Student attempt {attempt_index}/{total_attempts}")

        driver = self.driver
        wait = self.wait

        driver.get(row["quiz_url"])

        wait.until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        time.sleep(1)

        # Check nếu bị rớt login / guest
        page_text = driver.page_source.lower()
        if "guests cannot see or attempt quizzes" in page_text:
            raise Exception("Student is not logged in. Moodle opened quiz as guest.")

        # Attempt quiz hoặc Re-attempt quiz
        attempt_btn = wait.until(
            EC.presence_of_element_located((By.XPATH, row["attempt_button_xpath"]))
        )
        self.click_js(attempt_btn)

        # Start attempt nếu có
        try:
            start_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, row["start_button_id"]))
            )
            self.click_js(start_btn)
        except TimeoutException:
            pass

        time.sleep(1)

        # Sau khi start, thường đang ở trang question
        # Bấm Next page để qua Summary
        try:
            next_btn = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.ID, row["next_button_id"]))
            )
            self.click_js(next_btn)
            time.sleep(1)
        except TimeoutException:
            pass

        # Nếu có Finish attempt ... thì click tiếp
        try:
            finish_link = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.LINK_TEXT, row["finish_link_text"]))
            )
            self.click_js(finish_link)
            time.sleep(1)
        except TimeoutException:
            pass

        # Summary page: Submit all and finish
        submit_all_btn = wait.until(
            EC.presence_of_element_located((By.XPATH, row["submit_button_xpath"]))
        )
        self.click_js(submit_all_btn)

        time.sleep(1)

        # Trang confirm
        try:
            confirm_form_btn = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.XPATH, row["confirm_form_xpath"]))
            )
            self.click_js(confirm_form_btn)
            time.sleep(1)
        except TimeoutException:
            pass

        # Modal confirm cuối
        try:
            confirm_btn = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.XPATH, row["confirm_button_xpath"]))
            )
            self.click_js(confirm_btn)
        except TimeoutException:
            pass

        time.sleep(1.2)

    def prepare_bva_condition(self, row):
        # Dọn old attempts nếu có
        self.login(row["login_url"], row["teacher_user"], row["teacher_pass"])
        self.reset_attempts(row)
        self.set_attempts_allowed(row)
        self.logout_if_needed(row)

        self.login(row["login_url"], row["student_user"], row["student_pass"])

        attempts_used = int(row["attempts_used"])

        for i in range(attempts_used):
            self.do_quiz_attempt_once(row, i + 1, attempts_used)

    def verify_result(self, row):
        expected = row["expected_result"].lower().strip()

        self.driver.get(row["quiz_url"])
        time.sleep(2)

        page_text = self.driver.page_source.lower()

        print(f"[VERIFY] expected_result = {expected}")

        if expected == "attempt quiz":
            self.assertTrue(
                "attempt quiz" in page_text or "re-attempt quiz" in page_text,
                "Expected Attempt quiz/Re-attempt quiz button, but it was not found."
            )

        elif expected == "no more attempts":
            self.assertTrue(
                "no more attempts" in page_text
                or "no attempts allowed" in page_text
                or "attempt quiz" not in page_text,
                "Expected no more attempts, but attempt button still appears."
            )

        else:
            self.assertIn(
                expected,
                page_text,
                f"Expected text '{expected}' not found."
            )

    def run_bva_l2_case(self, row):
        test_id = row["test_id"]
        print(
            f"\nRunning {test_id} | allowed={row['attempts_allowed']} "
            f"| used={row['attempts_used']} | expected={row['expected_result']}"
        )

        try:
            self.prepare_bva_condition(row)
            self.verify_result(row)
            print(f"[PASS] {test_id}")

        finally:
            self.logout_if_needed(row)

            self.login(row["login_url"], row["teacher_user"], row["teacher_pass"])
            self.reset_attempts(row)
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
        self.run_bva_l2_case(row)

    return test


test_data = load_test_data("data/bva_l2_data.csv")

for row in test_data:
    test_name = f"test_{row['test_id'].replace('-', '_')}"
    setattr(QuizAttemptsBVALevel2, test_name, make_test(row))


if __name__ == "__main__":
    unittest.main(verbosity=2)
