import time
import unittest

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class SwipeMatchesUITest(unittest.TestCase):
    """
    Selenium UI tests for swipe and matches pages using Edge WebDriver.
    These tests assume that:
      - The dev server is running on http://127.0.0.1:8000
      - There exists at least one user that can log in and reach /swipe/
    Adjust LOGIN_EMAIL and LOGIN_PASSWORD to match a real user in your DB.
    """

    # Use an existing account in your DB that can log in and reach swipe.
    LOGIN_EMAIL = "jovanaceganjac@gmail.com"
    LOGIN_PASSWORD = "test123"

    @classmethod
    def setUpClass(cls):
        service = Service("./msedgedriver")
        cls.driver = webdriver.Edge(service=service)
        cls.driver.maximize_window()
        cls.wait = WebDriverWait(cls.driver, 10)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def login_and_open_swipe(self):
        d = self.driver
        w = self.wait

        d.get("http://127.0.0.1:8000/login/")
        try:
            email_input = w.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
            )
        except Exception:
            # Already logged in (logged_out_required redirected us), skip filling the form.
            email_input = None

        if email_input is not None:
            password_inputs = d.find_elements(By.CSS_SELECTOR, "input[type='password']")
            self.assertGreaterEqual(len(password_inputs), 1, "No password input on login page.")
            password_input = password_inputs[0]

            email_input.clear()
            password_input.clear()
            email_input.send_keys(self.LOGIN_EMAIL)
            password_input.send_keys(self.LOGIN_PASSWORD)

            submit_btn = d.find_element(By.XPATH, "//button[contains(., 'Login') or contains(., 'Sign in')]")
            submit_btn.click()

        # Either redirected directly to swipe or to some home, then click Find roommates link if exists.
        time.sleep(2)
        if "/swipe" not in d.current_url:
            try:
                swipe_link = d.find_element(By.XPATH, "//a[contains(@href, 'swipe')]")
                swipe_link.click()
            except Exception:
                pass

        self.assertIn("/swipe", d.current_url, "After login, user is not on swipe page.")

    def test_01_nav_from_swipe_to_my_profile_and_back(self):
        """From swipe page, My Profile link should open /my-profile/; Back on profile should return to /swipe/."""
        self.login_and_open_swipe()
        d = self.driver
        w = self.wait

        # Click My Profile in top nav
        my_profile_link = w.until(
            EC.element_to_be_clickable((By.XPATH, "//nav[contains(@class,'topbar__nav')]//a[contains(., 'My Profile')]"))
        )
        my_profile_link.click()
        time.sleep(1)
        self.assertIn("/my-profile/", d.current_url, "Click on My Profile did not navigate to /my-profile/.")

        # Click Back on My Profile page (btnBackView)
        back_btn = w.until(
            EC.element_to_be_clickable((By.ID, "btnBackView"))
        )
        back_btn.click()
        time.sleep(1)
        self.assertIn("/swipe", d.current_url, "Back from My Profile did not return to swipe page.")

    def test_02_nav_from_swipe_to_matches(self):
        """From swipe page, Matches link should navigate to /matches/."""
        self.login_and_open_swipe()
        d = self.driver
        w = self.wait

        matches_link = w.until(
            EC.element_to_be_clickable((By.XPATH, "//nav[contains(@class,'topbar__nav')]//a[contains(., 'Matches')]"))
        )
        matches_link.click()
        time.sleep(1)
        self.assertIn("/matches/", d.current_url, "Click on Matches did not navigate to /matches/.")

    def test_03_swipe_nav_like_advances_to_next_profile(self):
        """
        On swipe page, Like button should be clickable and advance to the next profile
        (or to empty state when there are no more profiles).
        """
        self.login_and_open_swipe()
        d = self.driver
        w = self.wait

        # Try to find swipe buttons; if there are no profiles (no buttons), skip the test.
        try:
            like_btn = w.until(EC.element_to_be_clickable((By.ID, "likeBtn")))
        except Exception:
            self.skipTest("No swipe buttons present (probably no suggested profiles).")
            return

        name_el = d.find_element(By.ID, "profileName")
        empty_state = d.find_element(By.ID, "emptyState")

        initial_name = name_el.text.strip()
        initial_empty_visible = empty_state.is_displayed()

        # Click like and wait a bit for UI to advance
        like_btn.click()
        time.sleep(0.8)

        new_name = name_el.text.strip()
        empty_after_like = empty_state.is_displayed()
        self.assertTrue(
            new_name != initial_name or (not initial_empty_visible and empty_after_like),
            "Like did not move to a different profile or empty state.",
        )


if __name__ == "__main__":
    unittest.main()

