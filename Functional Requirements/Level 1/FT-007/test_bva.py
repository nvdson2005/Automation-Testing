import csv
import time
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from preBVA import (
    prepare_bva,
    login,
    logout,
    reset_quiz_attempts,
    QUIZ_URL,
    TEACHER_USER,
    TEACHER_PASS,
)


def load_bva_data(file_path="data/bva_data.csv"):
    with open(file_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestBVA(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.driver = webdriver.Chrome()
        cls.driver.maximize_window()
        cls.wait = WebDriverWait(cls.driver, 60)

    def verify_result(self, expected_result):
        driver = self.driver

        driver.get(QUIZ_URL)
        time.sleep(3)

        page_text = driver.page_source.lower()
        expected_result = expected_result.lower().strip()

        print(f"[VERIFY] expected_result = {expected_result}")

        if expected_result == "attempt quiz":
            self.assertTrue(
                "attempt quiz" in page_text or "re-attempt quiz" in page_text,
                "Expected Attempt quiz/Re-attempt quiz button, but not found."
            )

        elif expected_result == "no more attempts":
            self.assertTrue(
                "no more attempts" in page_text
                or "no attempts allowed" in page_text
                or "attempt quiz" not in page_text,
                "Expected no more attempts, but attempt button still appears."
            )

        else:
            self.assertIn(
                expected_result,
                page_text,
                f"Expected text '{expected_result}' not found."
            )

    def run_bva_case(self, row):
        test_id = row["test_id"]
        attempts_allowed = row["attempts_allowed"]
        attempts_used = int(row["attempts_used"])
        expected_result = row["expected_result"]

        try:
            print(f"\n[CLEANUP BEFORE] Reset attempts before {test_id}")

            login(
                self.driver,
                self.wait,
                TEACHER_USER,
                TEACHER_PASS
            )

            reset_quiz_attempts(self.driver, self.wait)

            logout(self.driver, self.wait)

            prepare_bva(
                self.driver,
                self.wait,
                test_id,
                attempts_allowed,
                attempts_used
            )

            print(f"[TEST] Verify {test_id}")
            self.verify_result(expected_result)

        finally:
            print(f"[END] Finished {test_id}")
            logout(self.driver, self.wait)

    @classmethod
    def tearDownClass(cls):
        time.sleep(0.5)
        cls.driver.quit()


def make_test(row):
    def test(self):
        self.run_bva_case(row)

    return test


test_data = load_bva_data("data/bva_data.csv")

for row in test_data:
    test_name = f"test_{row['test_id'].replace('-', '_')}"
    setattr(TestBVA, test_name, make_test(row))


if __name__ == "__main__":
    unittest.main(verbosity=2)