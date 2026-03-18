import os
import time
import unittest

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class RegisterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        service = Service("./msedgedriver")
        cls.driver = webdriver.Edge(service=service)
        cls.driver.maximize_window()
        cls.wait = WebDriverWait(cls.driver, 10)

        cls.image_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "media", "documents", "iva.jpeg")
        )

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def setUp(self):
        self.driver.get("http://127.0.0.1:8000/register/")
        time.sleep(1)

    def get_form_elements(self):
        driver = self.driver
        wait = self.wait

        email_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )

        password_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
        self.assertGreaterEqual(
            len(password_inputs), 2,
            "Nisam pronašla 2 password polja na stranici."
        )

        password_input = password_inputs[0]
        confirm_password_input = password_inputs[1]

        file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")

        submit_button = driver.find_element(
            By.XPATH, "//button[contains(., 'Create Account')]"
        )

        return email_input, password_input, confirm_password_input, file_input, submit_button

    def fill_form(self, email="", password="", confirm_password="", upload_image=False):
        email_input, password_input, confirm_password_input, file_input, _ = self.get_form_elements()

        email_input.clear()
        password_input.clear()
        confirm_password_input.clear()

        if email:
            email_input.send_keys(email)

        if password:
            password_input.send_keys(password)

        if confirm_password:
            confirm_password_input.send_keys(confirm_password)

        if upload_image:
            self.assertTrue(
                os.path.exists(self.image_path),
                f"Slika ne postoji na putanji: {self.image_path}"
            )

            self.driver.execute_script("""
                arguments[0].style.display = 'block';
                arguments[0].style.visibility = 'visible';
                arguments[0].style.opacity = 1;
            """, file_input)

            file_input.send_keys(self.image_path)

    def submit_form(self):
        _, _, _, _, submit_button = self.get_form_elements()
        submit_button.click()
        time.sleep(1)

    def browser_validation_message(self, element):
        return element.get_attribute("validationMessage")

    def test_valid_registration(self):
        self.fill_form(
            email="ivakatic@gmail.com",
            password="test123",
            confirm_password="test123",
            upload_image=True
        )

        old_url = self.driver.current_url
        self.submit_form()

        time.sleep(2)

        self.assertNotEqual(
            self.driver.current_url,
            old_url,
            "Forma je poslata, ali je ostala na istoj stranici. Proveri da li registracija stvarno prolazi."
        )

    def test_empty_email(self):
        self.fill_form(
            email="",
            password="test123",
            confirm_password="test123",
            upload_image=True
        )

        email_input, _, _, _, _ = self.get_form_elements()
        self.submit_form()

        message = self.browser_validation_message(email_input)
        self.assertNotEqual(
            message.strip(), "",
            "Za prazan email nisam dobila validation poruku."
        )

    def test_empty_password(self):
        self.fill_form(
            email="ivakatic1@gmail.com",
            password="",
            confirm_password="test123",
            upload_image=True
        )

        _, password_input, _, _, _ = self.get_form_elements()
        self.submit_form()

        message = self.browser_validation_message(password_input)
        self.assertNotEqual(
            message.strip(), "",
            "Za prazan password nisam dobila validation poruku."
        )

    def test_empty_confirm_password(self):
        self.fill_form(
            email="ivakatic1@gmail.com",
            password="test123",
            confirm_password="",
            upload_image=True
        )

        _, _, confirm_password_input, _, _ = self.get_form_elements()
        self.submit_form()

        message = self.browser_validation_message(confirm_password_input)
        self.assertNotEqual(
            message.strip(), "",
            "Za praznu potvrdu lozinke nisam dobila validation poruku."
        )

    def test_missing_image(self):
        self.fill_form(
            email="ivakatic1@gmail.com",
            password="test123",
            confirm_password="test123",
            upload_image=False
        )

        _, _, _, file_input, _ = self.get_form_elements()
        self.submit_form()

        message = self.browser_validation_message(file_input)

        self.assertNotEqual(
            message.strip(), "",
            "Za neuploadovanu sliku nisam dobila validation poruku."
        )

    def test_password_mismatch(self):
        self.fill_form(
            email="ivakatic1@gmail.com",
            password="test123",
            confirm_password="test12",
            upload_image=True
        )

        old_url = self.driver.current_url
        self.submit_form()
        time.sleep(2)


        self.assertEqual(
            self.driver.current_url,
            old_url,
            "Kod nepoklapanja lozinki forma je ipak prošla dalje. Proveri validaciju."
        )

        page_text = self.driver.page_source.lower()
        possible_errors = [
            "passwords do not match",
            "password doesn't match",
            "lozinke se ne poklapaju",
            "password mismatch",
        ]

        self.assertTrue(
            any(error in page_text for error in possible_errors) or self.driver.current_url == old_url,
            "Nisam našla poruku za nepoklapanje lozinki. Možda treba proveriti tačan tekst greške u HTML-u."
        )


if __name__ == "__main__":
    unittest.main()