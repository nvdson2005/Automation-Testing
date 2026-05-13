import time
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


LOGIN_URL = "https://school.moodledemo.net/login/index.php"
COURSE_URL = "https://school.moodledemo.net/course/view.php?id=71"
PARTICIPANTS_URL = "https://school.moodledemo.net/user/index.php?id=71"

TEACHER_USER = "teacher"
TEACHER_PASS = "moodle26"
QUIZ_NAME = "AAA"


class PreECPSetup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = webdriver.Chrome()
        cls.driver.maximize_window()
        cls.wait = WebDriverWait(cls.driver, 60)

    def wait_page(self):
        try:
            self.wait.until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            pass

    def click_js(self, element):
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", element
        )
        time.sleep(0.3)
        self.driver.execute_script("arguments[0].click();", element)
        time.sleep(0.5)

    def login_teacher(self):
        driver = self.driver
        wait = self.wait

        for attempt in range(3):
            try:
                driver.get(LOGIN_URL)
                self.wait_page()

                username_box = wait.until(EC.presence_of_element_located((By.ID, "username")))
                password_box = wait.until(EC.presence_of_element_located((By.ID, "password")))

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
                    TEACHER_USER,
                    TEACHER_PASS,
                )

                login_btn = wait.until(EC.presence_of_element_located((By.ID, "loginbtn")))
                self.click_js(login_btn)
                time.sleep(2)
                return
            except Exception as e:
                print(f"    Login teacher retry {attempt + 1}/3: {type(e).__name__}")
                time.sleep(1)

        raise Exception("Teacher login failed after 3 retries")

    def logout(self):
        try:
            user_menu = self.wait.until(EC.presence_of_element_located((By.ID, "user-menu-toggle")))
            self.click_js(user_menu)
            logout_link = self.wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Log out")))
            self.click_js(logout_link)
            time.sleep(2)
        except Exception:
            pass

    def enrol_barbara_if_needed(self):
        print("[2/6] Check/enrol Barbara...")
        driver = self.driver
        wait = self.wait

        driver.get(PARTICIPANTS_URL)
        self.wait_page()
        time.sleep(1)

        if "barbara" in driver.page_source.lower():
            print("    Barbara already enrolled -> skip")
            return

        print("    Barbara not enrolled -> enrolling...")
        enrol_btn = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//input[@type='submit' and @value='Enrol users']"
                    " | //button[contains(.,'Enrol users')]"
                    " | //input[contains(@value,'Enrol users')]",
                )
            )
        )
        self.click_js(enrol_btn)
        time.sleep(2)

        search_box = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//input[@placeholder='Search' and contains(@id,'form_autocomplete_input')]",
                )
            )
        )
        search_box.clear()
        search_box.send_keys("Barbara")
        time.sleep(3)

        first_suggestion = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[contains(@id,'form_autocomplete_suggestions')]//li[1]")
            )
        )
        self.click_js(first_suggestion)
        time.sleep(1)

        save_btn = wait.until(
            EC.presence_of_element_located((By.XPATH, "//button[@data-action='save']"))
        )
        self.click_js(save_btn)
        time.sleep(2)
        print("    Barbara enrolled successfully")

    def get_existing_quiz_url(self):
        self.driver.get(COURSE_URL)
        self.wait_page()
        time.sleep(1)

        links = self.driver.find_elements(By.LINK_TEXT, QUIZ_NAME)
        if links:
            return links[0].get_attribute("href")
        return None

    def turn_edit_mode_on(self):
        print("[3/6] Turn edit mode on...")
        driver = self.driver
        wait = self.wait

        driver.get(COURSE_URL)
        self.wait_page()

        toggle = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//input[@name='setmode' and contains(@data-pageurl,'course/view.php')]",
                )
            )
        )

        if not toggle.is_selected():
            self.click_js(toggle)
            time.sleep(3)
        else:
            print("    Edit mode already on")

    def create_quiz_aaa(self):
        print("[4/6] Create Quiz AAA...")
        driver = self.driver
        wait = self.wait

        driver.get(COURSE_URL)
        self.wait_page()
        driver.execute_script("window.scrollTo(0, 300)")
        time.sleep(1)

        add_buttons = wait.until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//button[@data-action='open-addingcontent']")
            )
        )
        self.click_js(add_buttons[-1])
        time.sleep(1)

        chooser_buttons = wait.until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//button[@data-action='open-chooser']")
            )
        )
        self.click_js(chooser_buttons[0])
        time.sleep(1)

        quiz_option = wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Quiz")))
        self.click_js(quiz_option)
        time.sleep(1)

        add_btn = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//button[@data-action='add-selected-chooser-option']")
            )
        )
        self.click_js(add_btn)
        time.sleep(3)

        name_field = wait.until(EC.presence_of_element_located((By.ID, "id_name")))
        name_field.clear()
        name_field.send_keys(QUIZ_NAME)

        save_btn = wait.until(EC.presence_of_element_located((By.ID, "id_submitbutton")))
        self.click_js(save_btn)
        time.sleep(3)
        print("    Quiz AAA created")

    def add_numerical_question(self):
        print("[5/6] Add Numerical question...")
        driver = self.driver
        wait = self.wait

        questions_tab = wait.until(
            EC.presence_of_element_located((By.XPATH, "//a[normalize-space()='Questions']"))
        )
        self.click_js(questions_tab)
        time.sleep(1)

        add_menu = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//a[@data-bs-toggle='dropdown' and .//span[normalize-space()='Add']]",
                )
            )
        )
        self.click_js(add_menu)
        time.sleep(1)

        new_question = wait.until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(.,'a new question')]"))
        )
        self.click_js(new_question)
        time.sleep(1)

        numerical = wait.until(
            EC.presence_of_element_located((By.XPATH, "//*[normalize-space()='Numerical']"))
        )
        self.click_js(numerical)
        time.sleep(1)

        add_btn = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//input[@type='submit' and @value='Add']")
            )
        )
        self.click_js(add_btn)
        time.sleep(3)

        q_name = wait.until(EC.presence_of_element_located((By.ID, "id_name")))
        q_name.clear()
        q_name.send_keys("Hello?")

        # TinyMCE: set content directly; iframe send_keys is flaky in Moodle.
        wait.until(EC.presence_of_element_located((By.ID, "id_questiontext_ifr")))
        driver.execute_script(
            """
            if (window.tinyMCE && tinyMCE.get('id_questiontext')) {
                tinyMCE.get('id_questiontext').setContent('<p>hi</p>');
                tinyMCE.get('id_questiontext').fire('change');
            } else {
                const iframe = document.getElementById('id_questiontext_ifr');
                iframe.contentWindow.document.body.innerHTML = '<p>hi</p>';
            }
            """
        )
        time.sleep(1)

        answer = wait.until(EC.presence_of_element_located((By.ID, "id_answer_0")))
        answer.clear()
        answer.send_keys("50.5")

        tolerance = wait.until(EC.presence_of_element_located((By.ID, "id_tolerance_0")))
        tolerance.clear()
        tolerance.send_keys("49.5")

        Select(wait.until(EC.presence_of_element_located((By.ID, "id_fraction_0")))).select_by_value("1.0")

        submit_btn = wait.until(EC.presence_of_element_located((By.ID, "id_submitbutton")))
        self.click_js(submit_btn)
        time.sleep(3)
        print("    Numerical question added")

    # ---------- test ----------
    def test_setup(self):
        print("\n[1/6] Login teacher...")
        self.login_teacher()
        print("    Login OK")

        self.enrol_barbara_if_needed()

        existing_quiz_url = self.get_existing_quiz_url()
        if existing_quiz_url:
            print(f"[3-5/6] Quiz {QUIZ_NAME} already exists -> skip creation")
        else:
            self.turn_edit_mode_on()
            self.create_quiz_aaa()
            self.add_numerical_question()

        print("[6/6] Logout...")
        self.logout()
        print("\nSetup ECP completed!")

    @classmethod
    def tearDownClass(cls):
        time.sleep(1)
        try:
            cls.driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
