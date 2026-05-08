# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
import unittest, time, re

class FT001Prep(unittest.TestCase):
    def setUp(self):
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(30)
        self.base_url = "https://www.google.com/"
        self.verificationErrors = []
        self.accept_next_alert = True
    
    def test_f_t001_prep(self):
        driver = self.driver
        driver.get("https://school.moodledemo.net/")
        isNotLogin = self.is_element_present(By.XPATH, "/html/body/div[2]/nav/div/div[2]/div[5]/div/span/a")
        if isNotLogin == True :
            driver.find_element(By.LINK_TEXT, "Log in").click()
            driver.find_element(By.ID, "password").click()
            driver.find_element(By.ID, "username").click()
            driver.find_element(By.ID, "username").clear()
            driver.find_element(By.ID, "username").send_keys("teacher")
            driver.find_element(By.ID, "password").click()
            driver.find_element(By.ID, "password").clear()
            driver.find_element(By.ID, "password").send_keys("moodle26")
            driver.find_element(By.ID, "login").submit()
        else: 
            driver.execute_script("arguments[0].click();",
                driver.find_element(By.XPATH,
                    "//div[contains(@class,'usermenu')]//a[contains(@class,'dropdown-toggle')]"
                    " | //div[contains(@class,'usermenu')]//button[contains(@class,'dropdown-toggle')]"))
            driver.execute_script("arguments[0].click();",
                driver.find_element(By.XPATH, "//a[contains(@href,'logout')]"))
            driver.get("https://school.moodledemo.net/")
            driver.find_element(By.LINK_TEXT, "Log in").click()
            driver.find_element(By.ID, "username").click()
            driver.find_element(By.ID, "username").clear()
            driver.find_element(By.ID, "username").send_keys("teacher")
            driver.find_element(By.ID, "password").clear()
            driver.find_element(By.ID, "password").send_keys("moodle25")
            driver.find_element(By.ID, "login").submit()

        driver.get("https://school.moodledemo.net/course/view.php?id=59")
        el = driver.find_element(By.XPATH, "//li[@id='module-652']/div/div[2]/div[2]/div/div/a")
        driver.execute_script("arguments[0].click();", el)
        driver.execute_script("arguments[0].click();",
            driver.find_element(By.LINK_TEXT, "Settings"))

        isFileChecked = driver.find_element(By.ID, "id_assignsubmission_file_enabled").is_selected()
        if isFileChecked == True:
            driver.execute_script("arguments[0].click();",
                driver.find_element(By.ID, "id_assignsubmission_file_enabled"))

        isOnlineTextChecked = driver.find_element(By.ID, "id_assignsubmission_onlinetext_enabled").is_selected()
        if isOnlineTextChecked == False:
            driver.execute_script("arguments[0].click();",
                driver.find_element(By.ID, "id_assignsubmission_onlinetext_enabled"))

        isLimitChecked = driver.find_element(By.ID, "id_assignsubmission_onlinetext_wordlimit_enabled").is_selected()
        if isLimitChecked == False:
            driver.execute_script("arguments[0].click();",
                driver.find_element(By.ID, "id_assignsubmission_onlinetext_wordlimit_enabled"))

        limit_field = driver.find_element(By.ID, "id_assignsubmission_onlinetext_wordlimit")
        limit_field.clear()
        limit_field.send_keys("500")
        driver.execute_script("arguments[0].click();",
            driver.find_element(By.ID, "id_submitbutton2"))

        # Moodle Boost: "Log out" is inside a collapsed user-menu dropdown.
        # Open the dropdown first, then click the link.
        driver.execute_script("arguments[0].click();",
            driver.find_element(By.XPATH,
                "//div[contains(@class,'usermenu')]//a[contains(@class,'dropdown-toggle')]"
                " | //div[contains(@class,'usermenu')]//button[contains(@class,'dropdown-toggle')]"))
        driver.execute_script("arguments[0].click();",
            driver.find_element(By.XPATH, "//a[contains(@href,'logout')]"))
    
    def is_element_present(self, how, what):
        try: self.driver.find_element(by=how, value=what)
        except NoSuchElementException as e: return False
        return True
    
    def is_alert_present(self):
        try: self.driver.switch_to.alert
        except NoAlertPresentException as e: return False
        return True
    
    def close_alert_and_get_its_text(self):
        try:
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            if self.accept_next_alert:
                alert.accept()
            else:
                alert.dismiss()
            return alert_text
        finally: self.accept_next_alert = True
    
    def tearDown(self):
        self.driver.quit()
        self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    unittest.main()
