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
TEST_INPUT = "3.14"
EXPECTED_STATUS = "answer saved"
REPEAT_COUNT = 5

class ReliabilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = webdriver.Chrome()
        cls.driver.maximize_window()
        cls.wait = WebDriverWait(cls.driver, 60)
        cls.login()
    
    @classmethod
    def _click_js(self, element):
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", element
        )
        time.sleep(0.3)
        self.driver.execute_script("arguments[0].click();", element)
        time.sleep(0.5)

    @classmethod
    def login(cls):
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
                    USERNAME,
                    PASSWORD,
                )

                WebDriverWait(driver, 10).until(
                    lambda d: (
                        "login" not in d.current_url
                        or len(d.find_elements(By.ID, "user-menu-toggle")) > 0
                    )
                )

                print(f"Login OK: {USERNAME}")
                return

            except Exception as e:
                print(f"Login retry {attempt + 1}/3: {type(e).__name__}")
                time.sleep(0.5)

        raise Exception("Student login failed after 3 retries")

    def open_quiz(self):
        driver = self.driver
        wait = self.wait

        driver.get(COURSE_URL)

        wait.until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        time.sleep(2)

        quiz_links = wait.until(
            EC.presence_of_all_elements_located(
                (
                    By.XPATH,
                    f"//a[contains(@href,'/mod/quiz/view.php') and normalize-space()='{QUIZ_NAME}']"
                )
            )
        )

        quiz_link = quiz_links[-1]
        print("Selected quiz:", quiz_link.get_attribute("href"))

        self._click_js(quiz_link)
        time.sleep(2)
    
    def start_attempt(self):
        driver = self.driver
        wait = self.wait

        attempt_btn = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//button[contains(.,'ttempt quiz')]")
            )
        )
        self._click_js(attempt_btn)

        try:
            start_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "id_submitbutton"))
            )
            self._click_js(start_btn)
        except TimeoutException:
            pass

        time.sleep(2)

    def enter_answers(self, answer):
        wait = self.wait

        answer_input = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//span[contains(@class,'answer')]/input")
            )
        )

        answer_input.click()
        answer_input.clear()
        answer_input.send_keys(str(answer))

        time.sleep(0.5)

        next_btn = wait.until(
            EC.presence_of_element_located((By.ID, "mod_quiz-next-nav"))
        )

        self._click_js(next_btn)
        time.sleep(1)

    def submit_attempt(self):
        driver = self.driver
        try:
            submit_btn = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH, "//button[contains(normalize-space(.),'Submit all and finish')]"
                ))
            )
            self._click_js(submit_btn)
        except TimeoutException:
            print("Submit all and finish button not found; skip cleanup submit.")
            return
        time.sleep(0.5)

        try:
            confirm_form_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//form[@id='frm-finishattempt']/button")
                )
            )
            self._click_js(confirm_form_btn)
        except TimeoutException:
            pass

        try:
            confirm_modal_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[@data-action='save']")
                )
            )
            self._click_js(confirm_modal_btn)
        except TimeoutException:
            pass

        time.sleep(1)
    
    def test_reliability(self):
        print("\nNF007: Reliability - Answer Saving")
        print(f"Input answer: {TEST_INPUT}")
        print(f"Expected status: {EXPECTED_STATUS}")
        print(f"Repeat count: {REPEAT_COUNT}")

        success_count = 0

        for i in range(1, REPEAT_COUNT + 1):
            print(f"\n[Iteration {i}/{REPEAT_COUNT}]")

            with self.subTest(iteration=i):
                self.open_quiz()
                self.start_attempt()
                self.enter_answers(TEST_INPUT)

                page_text = self.driver.page_source.lower()
                is_saved = EXPECTED_STATUS in page_text

                if is_saved:
                    success_count += 1
                    print(f"Iteration {i}: PASS - Answer saved")
                else:
                    print(f"Iteration {i}: FAIL - Answer saved not found")

                # Submit attempt để lần sau có thể attempt mới
                self.submit_attempt()

                self.assertTrue(
                    is_saved,
                    f"Iteration {i}: Expected status '{EXPECTED_STATUS}' was not displayed."
                )

        print(f"\nReliability result: {success_count}/{REPEAT_COUNT} successful saves")

        self.assertEqual(
            success_count,
            REPEAT_COUNT,
            f"Reliability failed: only {success_count}/{REPEAT_COUNT} attempts were saved."
        )

    @classmethod
    def tearDownClass(cls):
        time.sleep(1)
        try:
            cls.driver.quit()
        except Exception:
            pass
if __name__ == "__main__":
    unittest.main(verbosity=2)
