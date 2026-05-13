import time
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


LOGIN_URL = "https://school.moodledemo.net/login/index.php"
COURSE_URL = "https://school.moodledemo.net/course/view.php?id=71"
PARTICIPANTS_URL = "https://school.moodledemo.net/user/index.php?id=71"
QUIZ_URL = "https://school.moodledemo.net/mod/quiz/view.php?id=1150"
REPORT_URL = "https://school.moodledemo.net/mod/quiz/report.php?id=1150&mode=overview"

TEACHER_USER = "teacher"
TEACHER_PASS = "moodle26"


class PreDTSetup(unittest.TestCase):
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

    def login_teacher(self):
        driver = self.driver

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
                    TEACHER_USER,
                    TEACHER_PASS,
                )

                WebDriverWait(driver, 10).until(
                    lambda d: (
                        "login" not in d.current_url
                        or len(d.find_elements(By.ID, "user-menu-toggle")) > 0
                    )
                )

                print("Login teacher OK")
                return

            except Exception as e:
                print(f"Login retry {attempt + 1}/3: {type(e).__name__}")
                time.sleep(0.5)

        raise Exception("Teacher login failed after 3 retries")

    def logout(self):
        try:
            user_menu = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "user-menu-toggle"))
            )
            self.click_js(user_menu)

            logout_link = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.LINK_TEXT, "Log out"))
            )
            self.click_js(logout_link)

            time.sleep(1)
            print("Logout teacher OK")

        except Exception:
            pass

    def enrol_barbara_if_needed(self):
        print("[PRE-DT] Check Barbara enrolment")

        driver = self.driver
        wait = self.wait

        driver.get(PARTICIPANTS_URL)
        time.sleep(3)

        page_text = driver.page_source.lower()

        if "barbara" in page_text:
            print("    Barbara already enrolled -> skip")
            return

        print("    Barbara not found -> enrolling...")

        try:
            enrol_btn = wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//input[@type='submit' and @value='Enrol users']"
                        " | //button[contains(.,'Enrol users')]"
                        " | //input[contains(@value,'Enrol users')]"
                    )
                )
            )
            self.click_js(enrol_btn)
            time.sleep(3)

            search_box = wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//input[@placeholder='Search' and contains(@id,'form_autocomplete_input')]"
                    )
                )
            )
            search_box.clear()
            search_box.send_keys("Barbara")
            time.sleep(3)

            first_suggestion = wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//*[contains(@id,'form_autocomplete_suggestions')]//li[1]"
                    )
                )
            )
            self.click_js(first_suggestion)
            time.sleep(2)

            save_btn = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[@data-action='save']")
                )
            )
            self.click_js(save_btn)
            time.sleep(3)

            print("    Barbara enrolled successfully")

        except TimeoutException:
            print("    Cannot find enrol UI. Maybe Barbara is already enrolled or page layout changed -> skip")

    def reset_attempts(self):
        print("[PRE-DT] Reset quiz attempts")

        driver = self.driver
        wait = self.wait

        driver.get(REPORT_URL)
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

        time.sleep(1)

    def set_attempts_allowed_5(self):
        print("[PRE-DT] Set Attempts allowed = 5")
        print("    Time limit setup skipped for R1-R3 because these are within-time rules.")

        driver = self.driver
        wait = self.wait

        driver.get(QUIZ_URL)

        wait.until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        settings_tab = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//a[normalize-space()='Settings']")
            )
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

        # Completion conditions = None if present.
        try:
            none_radio = driver.find_element(By.XPATH, "(//input[@type='radio'])[1]")
            self.click_js(none_radio)
        except Exception:
            pass

        attempts_dropdown = wait.until(
            EC.presence_of_element_located((By.ID, "id_attempts"))
        )

        driver.execute_script(
            """
            arguments[0].scrollIntoView({block:'center'});
            arguments[0].value = '5';
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """,
            attempts_dropdown,
        )

        selected_value = attempts_dropdown.get_attribute("value")
        print("    Selected attempts =", selected_value)

        if selected_value != "5":
            raise Exception(f"Failed to set attempts to 5. Got {selected_value}")

        save_btn = wait.until(
            EC.presence_of_element_located((By.ID, "id_submitbutton2"))
        )
        self.click_js(save_btn)

        wait.until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        time.sleep(1)

    def test_setup_dt(self):
        self.login_teacher()
        self.enrol_barbara_if_needed()
        self.reset_attempts()
        self.set_attempts_allowed_5()
        self.logout()

        print("DT precondition setup completed.")

    @classmethod
    def tearDownClass(cls):
        time.sleep(1)
        try:
            cls.driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
