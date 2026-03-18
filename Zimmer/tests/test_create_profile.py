import os
import time
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class CreateProfileTests(StaticLiveServerTestCase):

    def setUp(self):
        service = Service()
        self.browser = webdriver.Firefox(service=service)
        self.browser.maximize_window()

        self.wait = WebDriverWait(self.browser, 10)

        self.register_image_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "media", "documents", "iva.jpeg")
        )

        self.profile_photo_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "media", "profile_pics", "slika_iva.jpeg")
        )

        self.browser.get(self.live_server_url + "/register/")

        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )

        self.browser.find_element(By.CSS_SELECTOR, "input[type='email']").send_keys("test@test.com")

        password_inputs = self.browser.find_elements(By.CSS_SELECTOR, "input[type='password']")
        password_inputs[0].send_keys("test123")
        password_inputs[1].send_keys("test123")

        file_input = self.browser.find_element(By.CSS_SELECTOR, "input[type='file']")
        file_input.send_keys(self.register_image_path)

        self.browser.find_element(By.XPATH, "//button[contains(.,'Create Account')]").click()

        self.wait.until(EC.url_contains("create-profile"))

    def tearDown(self):
        self.browser.quit()

    def open_create_profile(self):
        self.browser.get(self.live_server_url + "/create-profile/")
        self.wait.until(
            EC.presence_of_element_located((By.NAME, "first_name"))
        )

    def submit_form(self):
        next_btn = self.browser.find_element(By.ID, "btnNext")
        self.browser.execute_script("arguments[0].scrollIntoView(true);", next_btn)
        time.sleep(0.3)
        next_btn.click()
        self.wait.until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

    def click_radio(self, name, value):
        radio = self.browser.find_element(
            By.XPATH, f"//input[@name='{name}' and @value='{value}']"
        )
        self.browser.execute_script("arguments[0].scrollIntoView(true);", radio)
        time.sleep(0.2)
        self.browser.execute_script("arguments[0].click();", radio)

    def fill_profile_form(
            self,
            first_name="Test",
            last_name="Test",
            dob="01.01.2000",
            jmbg="1234567890123",
            phone="+381601234567",
            occupation="Student",
            budget="200",
            profile_photo=True,
            has_accommodation="no",
            gender="male",
            has_pet="no",
            smoker="no",
            has_parties="no",
            has_partner="no",
            plays_instrument="no",
            preferred_type="apartment",
            city="Belgrade",
            location_radius="5"
    ):
        driver = self.browser

        if first_name:
            el = driver.find_element(By.NAME, "first_name")
            driver.execute_script("arguments[0].scrollIntoView(true);", el)
            time.sleep(0.2)
            el.send_keys(first_name)

        if last_name:
            el = driver.find_element(By.NAME, "last_name")
            driver.execute_script("arguments[0].scrollIntoView(true);", el)
            time.sleep(0.2)
            el.send_keys(last_name)

        if dob:
            el = driver.find_element(By.NAME, "date_of_birth")
            driver.execute_script("arguments[0].scrollIntoView(true);", el)
            time.sleep(0.2)
            el.send_keys(dob)

        if jmbg:
            el = driver.find_element(By.NAME, "id_number")
            driver.execute_script("arguments[0].scrollIntoView(true);", el)
            time.sleep(0.2)
            el.send_keys(jmbg)

        if phone:
            el = driver.find_element(By.NAME, "phone")
            driver.execute_script("arguments[0].scrollIntoView(true);", el)
            time.sleep(0.2)
            el.send_keys(phone)

        if occupation:
            el = driver.find_element(By.NAME, "occupation")
            driver.execute_script("arguments[0].scrollIntoView(true);", el)
            time.sleep(0.2)
            el.send_keys(occupation)

        budget_input = driver.find_element(By.NAME, "budget")
        driver.execute_script("arguments[0].scrollIntoView(true);", budget_input)
        time.sleep(0.2)
        budget_input.clear()
        budget_input.send_keys(budget)

        if profile_photo:
            photo_input = driver.find_element(By.ID, "profilePhoto")
            driver.execute_script("arguments[0].style.display='block';", photo_input)
            photo_input.send_keys(self.profile_photo_path)
            time.sleep(0.3)

        if has_accommodation:
            self.click_radio("has_accommodation", has_accommodation)

        if gender:
            self.click_radio("gender", gender)

        if has_pet:
            self.click_radio("has_pet", has_pet)

        if smoker:
            self.click_radio("smoker", smoker)

        if has_parties:
            self.click_radio("has_parties", has_parties)

        if has_partner:
            self.click_radio("has_partner", has_partner)

        if plays_instrument:
            self.click_radio("plays_instrument", plays_instrument)

        if has_accommodation == "no":
            if preferred_type:
                self.click_radio("preferred_type", preferred_type)

            if city:
                el = driver.find_element(By.NAME, "city")
                driver.execute_script("arguments[0].scrollIntoView(true);", el)
                time.sleep(0.2)
                el.send_keys(city)

            if location_radius:
                try:
                    el = self.wait.until(
                        EC.presence_of_element_located((By.NAME, "location_radius"))
                    )
                    driver.execute_script("arguments[0].scrollIntoView(true);", el)
                    time.sleep(0.2)
                    el.send_keys(location_radius)
                except Exception:
                    pass


    def test_01_all_fields_empty(self):
        """Forma ne sme da prodje kada su sva polja prazna."""
        self.open_create_profile()
        old_url = self.browser.current_url
        self.submit_form()
        self.assertEqual(
            self.browser.current_url,
            old_url,
            "Forma je prosla iako su sva polja prazna."
        )

    def test_02_empty_first_name(self):
        """Forma ne sme da prodje bez imena."""
        self.open_create_profile()
        self.fill_profile_form(first_name="")
        old_url = self.browser.current_url
        self.submit_form()
        self.assertEqual(self.browser.current_url, old_url,
                         "Forma je prosla bez first_name.")

    def test_03_empty_last_name(self):
        """Forma ne sme da prodje bez prezimena."""
        self.open_create_profile()
        self.fill_profile_form(last_name="")
        old_url = self.browser.current_url
        self.submit_form()
        self.assertEqual(self.browser.current_url, old_url,
                         "Forma je prosla bez last_name.")

    def test_04_empty_dob(self):
        """Forma ne sme da prodje bez datuma rodjenja."""
        self.open_create_profile()
        self.fill_profile_form(dob="")
        old_url = self.browser.current_url
        self.submit_form()
        self.assertEqual(self.browser.current_url, old_url,
                         "Forma je prosla bez date_of_birth.")

    def test_05_invalid_dob_format(self):
        """Forma ne sme da prodje sa pogresnim formatom datuma (yyyy-mm-dd umesto dd.mm.yyyy)."""
        self.open_create_profile()
        self.fill_profile_form(dob="2000-01-01")
        old_url = self.browser.current_url
        self.submit_form()
        self.assertEqual(self.browser.current_url, old_url,
                         "Forma je prosla sa pogresnim formatom datuma.")

    def test_06_jmbg_contains_letters(self):
        """JMBG ne sme da sadrzi slova."""
        self.open_create_profile()
        self.fill_profile_form(jmbg="abc123456789")
        old_url = self.browser.current_url
        self.submit_form()
        self.assertEqual(self.browser.current_url, old_url,
                         "Forma je prosla sa JMBG koji sadrzi slova.")

    def test_07_jmbg_less_than_13(self):
        """JMBG mora imati tacno 13 cifara - manje ne sme proci."""
        self.open_create_profile()
        self.fill_profile_form(jmbg="123456")
        old_url = self.browser.current_url
        self.submit_form()
        self.assertEqual(self.browser.current_url, old_url,
                         "Forma je prosla sa JMBG kracim od 13 cifara.")

    def test_08_jmbg_more_than_13(self):
        """JMBG mora imati tacno 13 cifara - vise ne sme proci."""
        self.open_create_profile()
        self.fill_profile_form(jmbg="123456789012345")
        old_url = self.browser.current_url
        self.submit_form()
        self.assertEqual(self.browser.current_url, old_url,
                         "Forma je prosla sa JMBG duzim od 13 cifara.")

    def test_09_empty_phone(self):
        """Forma ne sme da prodje bez broja telefona."""
        self.open_create_profile()
        self.fill_profile_form(phone="")
        old_url = self.browser.current_url
        self.submit_form()
        self.assertEqual(self.browser.current_url, old_url,
                         "Forma je prosla bez phone.")

    def test_10_invalid_phone_format(self):
        """Forma ne sme da prodje sa neispravnim formatom telefona."""
        self.open_create_profile()
        self.fill_profile_form(phone="abc123")
        old_url = self.browser.current_url
        self.submit_form()
        self.assertEqual(self.browser.current_url, old_url,
                         "Forma je prosla sa neispravnim formatom telefona.")

    def test_11_empty_city(self):
        """Forma ne sme da prodje bez grada."""
        self.open_create_profile()
        self.fill_profile_form(city="")
        old_url = self.browser.current_url
        self.submit_form()
        self.assertEqual(self.browser.current_url, old_url,
                         "Forma je prosla bez city.")

    def test_12_female_gender(self):
        """Forma treba da prodje na Part2 sa izabranim zenskim polom."""
        self.open_create_profile()
        self.fill_profile_form(gender="female")
        self.submit_form()
        part2 = self.wait.until(
            EC.visibility_of_element_located((By.ID, "formPart2"))
        )
        self.assertTrue(part2.is_displayed(),
                        "Forma nije presla na Part2 sa gender=female.")

    def test_13_accommodation_type_house(self):
        """Forma treba da prodje na Part2 sa preferred_type=house."""
        self.open_create_profile()
        self.fill_profile_form(preferred_type="house")
        self.submit_form()
        part2 = self.wait.until(
            EC.visibility_of_element_located((By.ID, "formPart2"))
        )
        self.assertTrue(part2.is_displayed(),
                        "Forma nije presla na Part2 sa preferred_type=house.")

    def test_14_accommodation_type_anyways(self):
        """Forma treba da prodje na Part2 sa preferred_type=anyways."""
        self.open_create_profile()
        self.fill_profile_form(preferred_type="anyways")
        self.submit_form()
        part2 = self.wait.until(
            EC.visibility_of_element_located((By.ID, "formPart2"))
        )
        self.assertTrue(part2.is_displayed(),
                        "Forma nije presla na Part2 sa preferred_type=anyways.")


    def go_to_part2(self):
        """Helper - popuni Part1 ispravno i predji na Part2."""
        self.open_create_profile()
        self.fill_profile_form()
        self.submit_form()
        self.wait.until(
            EC.visibility_of_element_located((By.ID, "formPart2"))
        )

    def fill_roommate_form(
            self,
            min_age="18",
            max_age="65",
            roommate_has_accommodation="no",
            roommate_gender="doesnt_matter",
            roommate_pet_ok="yes",
            roommate_smoker_ok="no",
            roommate_parties_ok="no",
            roommate_partner_ok="doesnt_matter",
            roommate_instrument_ok="yes"
    ):
        driver = self.browser

        if min_age:
            el = driver.find_element(By.NAME, "min_roommate_age")
            driver.execute_script("arguments[0].scrollIntoView(true);", el)
            el.clear()
            el.send_keys(min_age)
            time.sleep(0.2)

        if max_age:
            el = driver.find_element(By.NAME, "max_roommate_age")
            driver.execute_script("arguments[0].scrollIntoView(true);", el)
            el.clear()
            el.send_keys(max_age)
            time.sleep(0.2)

        if roommate_has_accommodation:
            self.click_radio("roommate_has_accommodation", roommate_has_accommodation)

        if roommate_gender:
            self.click_radio("roommate_gender", roommate_gender)

        if roommate_pet_ok:
            self.click_radio("roommate_pet_ok", roommate_pet_ok)

        if roommate_smoker_ok:
            self.click_radio("roommate_smoker_ok", roommate_smoker_ok)

        if roommate_parties_ok:
            self.click_radio("roommate_parties_ok", roommate_parties_ok)

        if roommate_partner_ok:
            self.click_radio("roommate_partner_ok", roommate_partner_ok)

        if roommate_instrument_ok:
            self.click_radio("roommate_instrument_ok", roommate_instrument_ok)

    def submit_part2(self):
        btn = self.browser.find_element(By.CSS_SELECTOR, "button.btn-submit")
        self.browser.execute_script("arguments[0].scrollIntoView(true);", btn)
        time.sleep(0.3)
        btn.click()
        self.wait.until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

    def test_17_part2_roommate_gender_male(self):
        """Part2 treba da prodje sa roommate_gender=male."""
        self.go_to_part2()
        self.fill_roommate_form(roommate_gender="male")
        old_url = self.browser.current_url
        self.submit_part2()
        self.assertNotEqual(self.browser.current_url, old_url,
                            "Forma nije prosla sa roommate_gender=male.")

    def test_18_part2_roommate_gender_female(self):
        """Part2 treba da prodje sa roommate_gender=female."""
        self.go_to_part2()
        self.fill_roommate_form(roommate_gender="female")
        old_url = self.browser.current_url
        self.submit_part2()
        self.assertNotEqual(self.browser.current_url, old_url,
                            "Forma nije prosla sa roommate_gender=female.")

    def test_19_part2_smoker_ok(self):
        """Part2 treba da prodje kada je pusac prihvatljiv."""
        self.go_to_part2()
        self.fill_roommate_form(roommate_smoker_ok="yes")
        old_url = self.browser.current_url
        self.submit_part2()
        self.assertNotEqual(self.browser.current_url, old_url,
                            "Forma nije prosla sa roommate_smoker_ok=yes.")

    def test_20_part2_valid_all_fields(self):
        """Part2 treba da prodje kada su sva polja ispravno popunjena."""
        self.go_to_part2()
        self.fill_roommate_form(
            min_age="18",
            max_age="65",
            roommate_has_accommodation="no",
            roommate_gender="doesnt_matter",
            roommate_pet_ok="yes",
            roommate_smoker_ok="no",
            roommate_parties_ok="no",
            roommate_partner_ok="doesnt_matter",
            roommate_instrument_ok="yes"
        )
        old_url = self.browser.current_url
        self.submit_part2()
        self.assertNotEqual(self.browser.current_url, old_url,
                            "Forma nije prosla iako su sva polja u Part2 ispravno popunjena.")

    def test_15_valid_form_all_fields(self):
        """Part1 treba da prodje na Part2 kada su sva polja ispravno popunjena."""
        self.open_create_profile()
        self.fill_profile_form(
            first_name="Test",
            last_name="Test",
            dob="01.01.2000",
            jmbg="1234567890123",
            phone="+381601234567",
            occupation="Student",
            budget="200",
            profile_photo=True,
            has_accommodation="no",
            gender="male",
            has_pet="no",
            smoker="no",
            has_parties="no",
            has_partner="no",
            plays_instrument="no",
            preferred_type="apartment",
            city="Belgrade",
            location_radius="5"
        )
        self.submit_form()
        part2 = self.wait.until(
            EC.visibility_of_element_located((By.ID, "formPart2"))
        )
        self.assertTrue(part2.is_displayed(),
                        "Forma nije presla na Part2 iako su sva polja ispravno popunjena.")

    def test_21_first_name_with_numbers(self):
        """Ne sme sme da se dozvoli ime sa brojevima."""
        self.open_create_profile()
        self.fill_profile_form(first_name="Test123")
        old_url = self.browser.current_url
        self.submit_form()
        self.assertEqual(self.browser.current_url, old_url,
                         "Forma je prosla sa imenm koji sadrzi brojeve.")

    def test_22_first_name_with_special_chars(self):
        """Ne sme sme da se dozvoli ime sa specijalnim znakovima."""
        self.open_create_profile()
        self.fill_profile_form(first_name="Te@st!")
        old_url = self.browser.current_url
        self.submit_form()
        self.assertEqual(self.browser.current_url, old_url,
                         "Forma je prosla sa imenom koje sadrzi specijalne znakove.")

    def test_23_last_name_with_numbers(self):
        """Ne sme sme da se dozvoli prezime sa brojevima."""
        self.open_create_profile()
        self.fill_profile_form(last_name="Test456")
        old_url = self.browser.current_url
        self.submit_form()
        self.assertEqual(self.browser.current_url, old_url,
                         "Forma je prosla sa prezimenom koje sadrzi brojeve.")

    def test_24_last_name_with_special_chars(self):
        """Ne sme sme da se dozvoli prezime sa specijalnim znakovima."""
        self.open_create_profile()
        self.fill_profile_form(last_name="Test*&^")
        old_url = self.browser.current_url
        self.submit_form()
        self.assertEqual(self.browser.current_url, old_url,
                         "Forma je prosla sa prezimenom koje sadrzi specijalne znakove.")

    def test_25_phone_with_letters(self):
        """Ne sme sme da se dozvoli telefon sa slovima."""
        self.open_create_profile()
        self.fill_profile_form(phone="abcdefghij")
        old_url = self.browser.current_url
        self.submit_form()
        self.assertEqual(self.browser.current_url, old_url,
                         "Forma je prosla sa telefonom koji sadrzi slova.")

    def test_26_phone_with_special_chars(self):
        """Ne sme sme da se dozvoli telefon sa specijalnim znakovima."""
        self.open_create_profile()
        self.fill_profile_form(phone="#@!$%^&*()")
        old_url = self.browser.current_url
        self.submit_form()
        self.assertEqual(self.browser.current_url, old_url,
                         "Forma je prosla sa telefonom koji sadrzi specijalne znakove.")

    def test_27_jmbg_with_hash_and_asterisk(self):
        """Ne sme sme da se dozvoli JMBG sa # i * znakovima."""
        self.open_create_profile()
        self.fill_profile_form(jmbg="#*34567890123")
        old_url = self.browser.current_url
        self.submit_form()
        self.assertEqual(self.browser.current_url, old_url,
                         "Forma je prosla sa JMBG koji sadrzi # i *.")

    def test_28_jmbg_with_dashes(self):
        """Ne sme sme da se dozvoli JMBG sa crticama."""
        self.open_create_profile()
        self.fill_profile_form(jmbg="123-456-789-01")
        old_url = self.browser.current_url
        self.submit_form()
        self.assertEqual(self.browser.current_url, old_url,
                         "Forma je prosla sa JMBG koji sadrzi crtice.")