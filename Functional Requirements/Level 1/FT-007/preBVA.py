import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException


LOGIN_URL = "https://school.moodledemo.net/login/index.php"
COURSE_URL = "https://school.moodledemo.net/course/view.php?id=71"
MY_COURSES_URL = "https://school.moodledemo.net/my/courses.php"
QUIZ_URL = "https://school.moodledemo.net/mod/quiz/view.php?id=1150"
PARTICIPANTS_URL = "https://school.moodledemo.net/user/index.php?id=71"
TEACHER_USER = "teacher"
TEACHER_PASS = "moodle26"

STUDENT_USER = "student"
STUDENT_PASS = "moodle26"


def wait_page(driver):
    time.sleep(0.5)
    try:
        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        pass


def click_js(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", element)


def login(driver, wait, username, password):
    for attempt in range(3):
        try:
            driver.get(LOGIN_URL)
            time.sleep(1)

            wait.until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            username_box = wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            password_box = wait.until(
                EC.presence_of_element_located((By.ID, "password"))
            )

            driver.execute_script("""
                const username = arguments[0];
                const password = arguments[1];
                const usernameValue = arguments[2];
                const passwordValue = arguments[3];

                username.value = usernameValue;
                password.value = passwordValue;

                username.dispatchEvent(new Event('input', { bubbles: true }));
                password.dispatchEvent(new Event('input', { bubbles: true }));
                username.dispatchEvent(new Event('change', { bubbles: true }));
                password.dispatchEvent(new Event('change', { bubbles: true }));
            """, username_box, password_box, username, password)

            login_btn = wait.until(
                EC.presence_of_element_located((By.ID, "loginbtn"))
            )
            driver.execute_script("arguments[0].click();", login_btn)

            time.sleep(0.5)
            return

        except Exception as e:
            print(f"    Login failed retry {attempt + 1}/3: {type(e).__name__}")
            time.sleep(1)

    raise Exception("Login failed after 3 retries")


def logout(driver, wait):
    try:
        user_menu = wait.until(
            EC.element_to_be_clickable((By.ID, "user-menu-toggle"))
        )
        user_menu.click()
        time.sleep(1)

        logout_link = wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Log out"))
        )
        logout_link.click()
        time.sleep(0.5)
    except Exception:
        pass


def enrol_barbara(driver, wait):
    print("[PRE] Check Barbara enrolment")

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
        click_js(driver, enrol_btn)
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
        click_js(driver, first_suggestion)
        time.sleep(0.5)

        save_btn = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//button[@data-action='save']")
            )
        )
        click_js(driver, save_btn)
        time.sleep(3)

        print("    Barbara enrolled successfully")

    except TimeoutException:
        print("    Cannot find enrol UI. Maybe Barbara is already enrolled or page layout changed -> skip")


def set_quiz_attempts(driver, wait, attempts_allowed):
    print(f"[PRE] Set attempts_allowed = {attempts_allowed}")

    driver.get(QUIZ_URL)

    wait.until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )

    settings_tab = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//a[normalize-space()='Settings']")
        )
    )
    click_js(driver, settings_tab)

    wait.until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )

    # Expand tất cả section đang bị collapse, thay vì tìm riêng Grade nhiều lần
    expand_icons = driver.find_elements(By.XPATH, "//span[@title='Expand']")
    for icon in expand_icons:
        try:
            click_js(driver, icon)
        except Exception:
            pass

    # Chọn Completion conditions = None nếu có
    try:
        none_radio = driver.find_element(By.XPATH, "(//input[@type='radio'])[1]")
        click_js(driver, none_radio)
    except Exception:
        pass

    # Set attempts bằng JS
    attempts_dropdown = wait.until(
        EC.presence_of_element_located((By.ID, "id_attempts"))
    )

    attempts_allowed = str(attempts_allowed).strip()

    if attempts_allowed.lower() == "unlimited":
        value = "0"
    else:
        value = attempts_allowed

    driver.execute_script("""
        arguments[0].scrollIntoView({block:'center'});
        arguments[0].value = arguments[1];
        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
    """, attempts_dropdown, value)

    selected_value = attempts_dropdown.get_attribute("value")
    print("Selected attempts =", selected_value)

    if selected_value != value:
        raise Exception(
            f"Failed to set attempts. Expected {value}, got {selected_value}"
        )

    save_btn = wait.until(
        EC.presence_of_element_located((By.ID, "id_submitbutton2"))
    )
    click_js(driver, save_btn)

    wait.until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def do_quiz_attempt_once(driver, wait, attempt_index, total_attempts):
    print(f"[PRE] Student attempt {attempt_index}/{total_attempts}")

    driver.get(QUIZ_URL)
    time.sleep(0.5)

    # Attempt quiz hoặc Re-attempt quiz
    attempt_btn = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//button[contains(.,'ttempt quiz')]")
        )
    )
    click_js(driver, attempt_btn)
    time.sleep(0.5)

    # Start attempt button nếu Moodle hiện confirm page
    try:
        start_btn = wait.until(
            EC.presence_of_element_located((By.ID, "id_submitbutton"))
        )
        click_js(driver, start_btn)
        time.sleep(0.5)
    except Exception:
        pass

    # Finish attempt ...
    finish_link = wait.until(
        EC.presence_of_element_located((By.LINK_TEXT, "Finish attempt ..."))
    )
    click_js(driver, finish_link)
    time.sleep(0.5)

    # Submit all and finish
    submit_all_btn = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//form[@id='frm-finishattempt']/button")
        )
    )
    click_js(driver, submit_all_btn)
    time.sleep(0.5)

    # Confirm submit
    confirm_btn = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//button[@data-action='save']")
        )
    )
    click_js(driver, confirm_btn)
    time.sleep(1)

def reset_quiz_attempts(driver, wait):
    print("[CLEANUP] Reset quiz attempts")

    report_url = "https://school.moodledemo.net/mod/quiz/report.php?id=1150&mode=overview"
    driver.get(report_url)
    time.sleep(3)

    page_text = driver.page_source.lower()

    if (
        "no attempts have been made" in page_text
        or "nothing to display" in page_text
        or "no attempts" in page_text
    ):
        print("    No attempts found -> skip reset")
        return

    # Tick tất cả attempt checkbox
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
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                checkbox
            )
            time.sleep(0.2)

            if checkbox.is_enabled() and not checkbox.is_selected():
                driver.execute_script("arguments[0].click();", checkbox)

        except Exception:
            pass

    time.sleep(1)

    # Click Delete selected attempts
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

        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});",
            delete_btn
        )
        time.sleep(1)
        driver.execute_script("arguments[0].click();", delete_btn)

    except TimeoutException:
        print("    Delete selected attempts button not found -> skip reset")
        return

    time.sleep(0.5)

    # Confirm Yes / Continue
    try:
        confirm_btn = wait.until(
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

        driver.execute_script("arguments[0].click();", confirm_btn)
        time.sleep(3)

        print("    Attempts reset successfully")

    except TimeoutException:
        print("    Confirm button not found, maybe attempts were already deleted")

def prepare_bva(driver, wait, test_id, attempts_allowed, attempts_used):
    print(f"\n===== PREPARE {test_id} =====")
    print(f"attempts_allowed = {attempts_allowed}")
    print(f"attempts_used    = {attempts_used}")

    print("[1] Login teacher")
    login(driver, wait, TEACHER_USER, TEACHER_PASS)

    print("[2] Enrol Barbara if needed")
    enrol_barbara(driver, wait)

    print("[3] Set quiz attempts")
    set_quiz_attempts(driver, wait, attempts_allowed)

    print("[4] Logout teacher")
    logout(driver, wait)

    print("[5] Login student")
    login(driver, wait, STUDENT_USER, STUDENT_PASS)

    print(f"[6] Student does quiz {attempts_used} time(s)")
    for i in range(int(attempts_used)):
        do_quiz_attempt_once(driver, wait, i + 1, int(attempts_used))

    print(f"Precondition done for {test_id}")