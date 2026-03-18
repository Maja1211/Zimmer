from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse

from app.models import (
    Account,
    UserProfile,
    UserPreferences,
    Housing,
)
from app.views import _validate_edit_profile_form, UserType

# Ime, prezime, JMBG i datum rođenja se NE MOGU menjati pri izmeni profila
JOVANA_ANDRIC_READONLY = {
    'first_name': 'Jovana',
    'last_name': 'Andric',
    'id_number': '1109004500010',
    'date_of_birth': '11.09.2004',
}


def _valid_edit_form_data(overrides=None):
    data = {
        **JOVANA_ANDRIC_READONLY,
        'phone': '+381611111120',
        'city': 'Beograd',
        'occupation': 'student',
        'budget': '500',
        'has_accommodation': 'no',
        'gender': 'female',
        'has_pet': 'no',
        'smoker': 'no',
        'has_parties': 'no',
        'has_partner': 'no',
        'plays_instrument': 'no',
        'preferred_type': 'apartment',
        'min_roommate_age': '18',
        'max_roommate_age': '65',
        'roommate_has_accommodation': 'no',
        'roommate_gender': 'doesnt_matter',
    }
    if overrides:
        data.update(overrides)
    return data


class TestEditProfileValidation(TestCase):
    """Jedinični testovi za funkciju _validate_edit_profile_form."""

    def test_valid_data_no_accommodation(self):
        section, msg = _validate_edit_profile_form(_valid_edit_form_data())
        self.assertIsNone(section)
        self.assertIsNone(msg)

    def test_valid_data_with_accommodation(self):
        data = _valid_edit_form_data({
            'has_accommodation': 'yes',
            'accommodation_type': 'apartment',
            'accommodation_rent': '250',
            'accommodation_address': 'Street 1',
            'accommodation_lat': '44.8176',
            'accommodation_lon': '20.4633',
        })
        section, msg = _validate_edit_profile_form(data)
        self.assertIsNone(section)
        self.assertIsNone(msg)

    def test_invalid_phone(self):
        data = _valid_edit_form_data({'phone': '123'})
        section, msg = _validate_edit_profile_form(data)
        self.assertEqual(section, 'validationMessageBasic')
        self.assertIn('Phone', msg)

    def test_city_required_when_no_accommodation(self):
        data = _valid_edit_form_data({'has_accommodation': 'no', 'city': ''})
        section, msg = _validate_edit_profile_form(data)
        self.assertEqual(section, 'validationMessageAccommodation')
        self.assertIn('City', msg)

    def test_budget_required_when_no_accommodation(self):
        data = _valid_edit_form_data({'budget': ''})
        section, msg = _validate_edit_profile_form(data)
        self.assertEqual(section, 'validationMessageBasic')
        self.assertIn('Budget', msg)

    def test_budget_positive_when_no_accommodation(self):
        data = _valid_edit_form_data({'budget': '0'})
        section, msg = _validate_edit_profile_form(data)
        self.assertEqual(section, 'validationMessageBasic')

    def test_gender_required(self):
        data = _valid_edit_form_data({'gender': ''})
        section, msg = _validate_edit_profile_form(data)
        self.assertEqual(section, 'validationMessageAbout')
        self.assertIn('Gender', msg)

    def test_accommodation_type_required_when_has_accommodation(self):
        data = _valid_edit_form_data({
            'has_accommodation': 'yes',
            'accommodation_type': '',
            'accommodation_rent': '200',
        })
        section, msg = _validate_edit_profile_form(data)
        self.assertEqual(section, 'validationMessageAbout')
        self.assertIn('accommodation type', msg.lower())

    def test_rent_required_when_has_accommodation(self):
        data = _valid_edit_form_data({
            'has_accommodation': 'yes',
            'accommodation_type': 'apartment',
            'accommodation_rent': '',
        })
        section, msg = _validate_edit_profile_form(data)
        self.assertEqual(section, 'validationMessageAbout')
        self.assertIn('rent', msg.lower())

    def test_preferred_type_required_when_no_accommodation(self):
        data = _valid_edit_form_data({'preferred_type': ''})
        section, msg = _validate_edit_profile_form(data)
        self.assertEqual(section, 'validationMessageAccommodation')
        self.assertIn('preferred', msg.lower())


class TestMyProfileView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.account = Account.objects.create(
            email='jovanaandric@gmail.com',
            passwordhash='dummy',
            status='ACTIVE',
        )

        cls.profile = UserProfile.objects.create(
            idacc=cls.account,
            jmbg=JOVANA_ANDRIC_READONLY['id_number'],
            phonenumber='+381611111120',
            name=JOVANA_ANDRIC_READONLY['first_name'],
            surname=JOVANA_ANDRIC_READONLY['last_name'],
            dateofbirth=date(2004, 9, 11),
            budget=Decimal('500'),
            hashousing=False,
            sex='female',
            smoker='no',
            party='rarely',
            partner='no',
        )
        cls.preferences = UserPreferences.objects.create(
            idacc=cls.profile,
            preferred_sex='doesnt_matter',
            minimumage=18,
            maximumage=99,
        )

    def _login_as_profile_user(self, client):
        session = client.session
        session['user_id'] = self.account.idacc
        session['user_type'] = UserType.UNVERIFIED.value
        session.save()

    def test_my_profile_get_redirects_when_not_logged_in(self):
        client = Client()
        response = client.get(reverse('my_profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_my_profile_get_returns_200_when_logged_in(self):
        client = Client()
        self._login_as_profile_user(client)
        response = client.get(reverse('my_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('profile', response.context)

    def test_my_profile_get_context_contains_profile_data(self):
        client = Client()
        self._login_as_profile_user(client)
        response = client.get(reverse('my_profile'))
        profile = response.context.get('profile')
        self.assertIsNotNone(profile)
        self.assertEqual(profile.get('first_name'), self.profile.name)
        self.assertEqual(profile.get('last_name'), self.profile.surname)

    def test_my_profile_post_valid_redirects_to_my_profile(self):
        client = Client()
        self._login_as_profile_user(client)
        data = _valid_edit_form_data({'occupation': 'zaposlen', 'budget': '600'})
        response = client.post(reverse('my_profile'), data, follow=False)
        self.assertRedirects(response, reverse('my_profile'))

    def test_my_profile_post_valid_updates_profile_in_db(self):
        client = Client()
        self._login_as_profile_user(client)
        # Menjamo samo polja koja se mogu menjati (ne ime, prezime, JMBG, datum)
        data = _valid_edit_form_data({
            'occupation': 'zaposlen',
            'budget': '600',
            'smoker': 'yes',
        })
        client.post(reverse('my_profile'), data)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.occupation, 'zaposlen')
        self.assertEqual(self.profile.budget, Decimal('600'))
        self.assertEqual(self.profile.smoker, 'yes')
        self.assertEqual(self.profile.name, 'Jovana')
        self.assertEqual(self.profile.surname, 'Andric')

    def test_my_profile_post_invalid_returns_form_with_error(self):
        client = Client()
        self._login_as_profile_user(client)
        data = _valid_edit_form_data({'phone': '123'})
        response = client.post(reverse('my_profile'), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', response.context)
        self.assertIn('error_section', response.context)
        self.assertEqual(response.context['error_section'], 'validationMessageBasic')

    def test_my_profile_post_invalid_does_not_change_profile(self):
        client = Client()
        self._login_as_profile_user(client)
        original_name = self.profile.name
        data = _valid_edit_form_data({'phone': 'invalid'})
        client.post(reverse('my_profile'), data)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.name, original_name)


class TestProfileEditModels(TestCase):
    def test_user_profile_save_after_edit_fields(self):
        account = Account.objects.create(
            email='model_test@example.com', passwordhash='x', status='ACTIVE'
        )
        dob = date.today() - timedelta(days=365 * 25)
        profile = UserProfile.objects.create(
            idacc=account,
            jmbg='1505990800124',
            phonenumber='+381912345679',
            name='Old',
            surname='Name',
            dateofbirth=dob,
            budget=Decimal('100'),
            hashousing=False,
            sex='male',
            smoker='no',
            party='no',
            partner='no',
        )
        profile.name = 'NewName'
        profile.budget = Decimal('350')
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.name, 'NewName')
        self.assertEqual(profile.budget, Decimal('350'))

    def test_user_preferences_save_after_edit(self):
        account = Account.objects.create(
            email='prefs_test@example.com', passwordhash='x', status='ACTIVE'
        )
        dob = date.today() - timedelta(days=365 * 22)
        profile = UserProfile.objects.create(
            idacc=account,
            jmbg='1505990800125',
            phonenumber='+381912345670',
            name='P',
            surname='S',
            dateofbirth=dob,
            budget=Decimal('200'),
            hashousing=False,
            sex='female',
            smoker='no',
            party='no',
            partner='no',
        )
        prefs = UserPreferences.objects.create(
            idacc=profile,
            city='Novi Sad',
            minimumage=20,
            maximumage=70,
        )
        prefs.city = 'Belgrade'
        prefs.minimumage = 21
        prefs.save()
        prefs.refresh_from_db()
        self.assertEqual(prefs.city, 'Belgrade')
        self.assertEqual(prefs.minimumage, 21)

    def test_housing_deleted_when_user_switches_to_no_accommodation(self):
        account = Account.objects.create(
            email='housing_test@example.com', passwordhash='x', status='ACTIVE'
        )
        dob = date.today() - timedelta(days=365 * 23)
        profile = UserProfile.objects.create(
            idacc=account,
            jmbg='1505990800126',
            phonenumber='+381912345671',
            name='H',
            surname='U',
            dateofbirth=dob,
            budget=Decimal('0'),
            hashousing=True,
            lot_type='apartment',
            sex='other',
            smoker='no',
            party='no',
            partner='no',
        )
        housing = Housing.objects.create(
            owneridacc=profile,
            lot_type='apartment',
            rent=Decimal('300'),
        )
        self.assertTrue(Housing.objects.filter(owneridacc=profile).exists())
        housing.delete()
        profile.hashousing = False
        profile.lot_type = None
        profile.save()
        self.assertFalse(Housing.objects.filter(owneridacc=profile).exists())
