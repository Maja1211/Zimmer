
import os
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from app.models import Account, UserProfile, UserPreferences



class CreateProfileUnitTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse("create_profile")

        self.account = Account.objects.create(
            email="test@test.com",
            passwordhash="testhash",
            status="ACTIVE"
        )


        import shutil
        from django.conf import settings
        src = os.path.join(settings.BASE_DIR, "media", "documents", "iva.jpeg")
        dst_name = f"documents/id_{self.account.idacc}.jpg"
        dst_full = os.path.join(settings.MEDIA_ROOT, dst_name)
        os.makedirs(os.path.dirname(dst_full), exist_ok=True)
        shutil.copy2(src, dst_full)
        self.doc_path = dst_name

        session = self.client.session
        session['user_id'] = self.account.idacc
        session['user_email'] = self.account.email
        session['user_type'] = 2
        session.save()

        self.profile_photo_path = os.path.join(
            settings.BASE_DIR, "media", "profile_pics", "slika_iva.jpeg"
        )

        self.valid_data = {
            "first_name": "Test",
            "last_name": "Test",
            "date_of_birth": "01.01.2000",
            "id_number": "1234567890123",
            "phone": "+381601234567",
            "budget": "200",
            "has_accommodation": "no",
            "gender": "male",
            "has_pet": "no",
            "smoker": "no",
            "has_parties": "no",
            "has_partner": "no",
            "plays_instrument": "no",
            "preferred_type": "apartment",
            "city": "Belgrade",
        }

    def tearDown(self):
        try:
            from django.conf import settings
            full = os.path.join(settings.MEDIA_ROOT, self.doc_path)
            if os.path.exists(full):
                os.remove(full)
        except Exception:
            pass

    def get_fresh_photo(self):
        with open(self.profile_photo_path, "rb") as f:
            return SimpleUploadedFile(
                "slika_iva.jpeg",
                f.read(),
                content_type="image/jpeg"
            )

    def post(self, overrides={}):
        data = {**self.valid_data, **overrides, "profile_photo": self.get_fresh_photo()}
        return self.client.post(self.url, data, format='multipart')

    def test_create_profile_requires_login(self):
        """Pristup stranici nije dozvoljen bez prijave."""
        self.client.session.flush()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_post_without_login_redirects(self):
        """Slanje forme bez prijave rezultuje preusmeravanjem."""
        self.client.session.flush()
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_valid_data_accepted(self):
        """Ispravno popunjena forma se uspjesno obradjuje."""
        response = self.post()
        self.assertEqual(response.status_code, 302)

    def test_user_profile_saved_in_database(self):
        """Nakon kreiranja profila, UserProfile postoji u bazi."""
        self.post()
        self.assertTrue(
            UserProfile.objects.filter(idacc=self.account).exists()
        )

    def test_user_preferences_saved_in_database(self):
        """Nakon kreiranja profila, UserPreferences postoje u bazi."""
        self.post()
        profile = UserProfile.objects.get(idacc=self.account)
        self.assertTrue(
            UserPreferences.objects.filter(idacc=profile).exists()
        )

    def test_profile_name_saved_correctly(self):
        """Ime korisnika je ispravno sacuvano u bazi."""
        self.post({"first_name": "Marija"})
        profile = UserProfile.objects.get(idacc=self.account)
        self.assertEqual(profile.name, "Marija")

    def test_profile_surname_saved_correctly(self):
        """Prezime korisnika je ispravno sacuvano u bazi."""
        self.post({"last_name": "Petrovic"})
        profile = UserProfile.objects.get(idacc=self.account)
        self.assertEqual(profile.surname, "Petrovic")

    def test_profile_sex_saved_correctly(self):
        """Pol korisnika je ispravno sacuvan u bazi."""
        self.post({"gender": "female"})
        profile = UserProfile.objects.get(idacc=self.account)
        self.assertEqual(profile.sex, "female")

    def test_profile_jmbg_saved_correctly(self):
        """JMBG korisnika je ispravno sacuvan u bazi."""
        self.post({"id_number": "1234567890123"})
        profile = UserProfile.objects.get(idacc=self.account)
        self.assertEqual(profile.jmbg, "1234567890123")

    def test_preferences_city_saved_correctly(self):
        """Grad korisnika je ispravno sacuvan u UserPreferences."""
        self.post({"city": "Novi Sad"})
        profile = UserProfile.objects.get(idacc=self.account)
        prefs = UserPreferences.objects.get(idacc=profile)
        self.assertEqual(prefs.city, "Novi Sad")

    def test_preferences_preferred_type_saved_correctly(self):
        """Preferirani tip smestaja je ispravno sacuvan u UserPreferences."""
        self.post({"preferred_type": "house"})
        profile = UserProfile.objects.get(idacc=self.account)
        prefs = UserPreferences.objects.get(idacc=profile)
        self.assertIsNone(prefs.lot_type)