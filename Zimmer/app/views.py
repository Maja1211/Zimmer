"""
Zimmer app views (registration, login, profile, swipe, matches).
Authors: Jovana Ceganjac 2022/0423 (create profile, my profile, edit, delete),
         Milica Eva Stojanovic 2022/0361 (create profile, algorithm, swipe),
         Maja Spirto 2022/0572 (home, algorithm, swipe, matches),
         Luka Rapaic 2022/0266 (login, registration).
"""
import hashlib
import math
import re
import time
import urllib.parse
import urllib.request
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import wraps
from json import loads as json_loads
from enum import Enum

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.templatetags.static import static
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from .models import (
    Account,
    Housing,
    LOT_TYPE_PREF_VALUES,
    LOT_TYPE_VALUES,
    PARTNER_PREF_VALUES,
    PARTNER_VALUES,
    PARTY_VALUES,
    PREFERRED_SEX_VALUES,
    Preferenceinstrument,
    Preferencepet,
    ROOMMATE_HAS_ACCOMMODATION_PREF_VALUES,
    SEX_VALUES,
    SMOKER_VALUES,
    UserPreferences,
    UserProfile,
    Matches
)
from .models import Swipes, Unverifiedaccounts, Moderator
from django.core.files.storage import default_storage

class UserType(Enum):
    """Session user type: moderator, new user, unverified, or verified."""
    MODERATOR = 1
    NEW_REGISTRATION = 2
    UNVERIFIED = 3
    VERIFIED = 4


# ----- A logged-out user -----
def logged_out_required(view_func):
    """Allow only logged-out users; redirect others to home/create_profile/moderator."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        if not user_id:
            return view_func(request, *args, **kwargs)

        user_type = UserType(request.session.get('user_type'))
        if user_type == UserType.MODERATOR:
            return redirect('moderator')
        if user_type == UserType.NEW_REGISTRATION:
            return redirect('create_profile')

        return redirect('swipe')
    return wrapper

# ----- Any logged-in user -----
def login_required(view_func):
    """Require login; redirect to login page otherwise."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

# ----- Only users who finished creating their profiles -----
def profile_required(view_func):
    """Require that user has completed profile; redirect to login or create_profile otherwise."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('user_id')

        if not user_id:
            return redirect('login')

        user_type = UserType(request.session.get('user_type'))
        if user_type is UserType.MODERATOR:
            return redirect('moderator_page')

        if user_type is UserType.NEW_REGISTRATION:
            return redirect('create_profile')

        return view_func(request, *args, **kwargs)

    return wrapper

# ----- Only verified users -----
def verified_required(view_func):
    """Require verified account; unverified users are redirected to swipe."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('user_id')

        if not user_id:
            return redirect('login')

        user_type = UserType(request.session.get('user_type'))
        if user_type is UserType.MODERATOR:
            return redirect('moderator_page')

        if user_type is UserType.NEW_REGISTRATION:
            return redirect('create_profile')

        if user_type is UserType.UNVERIFIED:
            return redirect('swipe')

        return view_func(request, *args, **kwargs)
    return wrapper

# ----- Only moderators -----
def moderator_required(view_func):
    """Allow only moderators; others are redirected to swipe."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('user_id')

        if not user_id:
            return redirect('login')

        user_type = UserType(request.session.get('user_type'))

        if user_type is not UserType.MODERATOR:
            return redirect('swipe')

        return view_func(request, *args, **kwargs)
    return wrapper


def get_current_user_profile(request):
    """Return the current user's UserProfile from session, or None if not logged in or no profile."""
    user_id = request.session.get('user_id')
    if not user_id:
        return None

    return (
        UserProfile.objects
        .filter(idacc_id=user_id)
        .select_related('userpreferences')
        .prefetch_related('userpreferences__pets', 'userpreferences__instruments')
        .first()
    )


def _get_lookup_value(obj):
    """Get display value from a lookup model instance (Preferencepet, etc.) or enum string."""
    if obj is None:
        return ''
    return getattr(obj, 'value', str(obj))


def profile_to_context(up, prefs, housing, request):
    """Build profile dict for my_profile template from UserProfile, UserPreferences, Housing. Returns dict of form fields."""
    if up is None:
        return None

    profile_photo_url = ''
    if up.profilephotourl:
        profile_photo_url = request.build_absolute_uri(settings.MEDIA_URL + up.profilephotourl)
    date_str = up.dateofbirth.strftime('%d.%m.%Y') if up.dateofbirth else ''
    has_accommodation = 'Yes' if up.hashousing else 'No'
    # When user has accommodation: address is the housing address (where coordinates point to), not city
    accommodation_address = (housing.address or '') if housing else ''
    accommodation_type = (housing.lot_type or '') if housing else ''
    housing_rent = str(housing.rent) if housing and housing.rent is not None else ''
    accommodation_lat = str(housing.locationcoordlat) if housing and housing.locationcoordlat is not None else ''
    accommodation_lon = str(housing.locationcoordlon) if housing and housing.locationcoordlon is not None else ''

    profile = {
        'profile_photo_url': profile_photo_url,
        'first_name': up.name or '',
        'last_name': up.surname or '',
        'date_of_birth': date_str,
        'id_number': up.jmbg or '',
        'phone': up.phonenumber or '',
        'occupation': up.occupation or '',
        'budget': '' if up.hashousing else (str(up.budget) if up.budget is not None else ''),
        'has_accommodation': has_accommodation,
        'accommodation_address': accommodation_address,
        'accommodation_type': accommodation_type,
        'housing_rent': housing_rent,
        'accommodation_lat': accommodation_lat,
        'accommodation_lon': accommodation_lon,
        'gender': up.sex or '',
        'has_pet': 'Yes' if up.pets.exclude(value__iexact='no').exists() else 'No',
        'pet_type': ', '.join(p.value for p in up.pets.exclude(value__iexact='yes').exclude(value__iexact='no')) or '',
        'smoker': up.smoker or '',
        'has_parties': 'Yes' if (up.party or 'no') != 'no' else 'No',
        'party_frequency': up.party or '',
        'has_partner': up.partner or '',
        'plays_instrument': 'Yes' if up.instruments.exclude(value__iexact='no').exists() else 'No',
        'instrument_name': ', '.join(i.value for i in up.instruments.exclude(value__iexact='yes').exclude(value__iexact='no')) or '',
        'preferred_type': '',
        'min_roommate_age': '',
        'max_roommate_age': '',
        'city': '',
        'preferred_location': '',
        'location_radius': '',
        'roommate_has_accommodation': 'No',
        'roommate_gender': "Doesn't matter",
        'roommate_pet_ok': 'Yes',
        'roommate_smoker_ok': 'No',
        'roommate_parties_ok': 'Yes',
        'roommate_partner_ok': "Doesn't matter",
        'roommate_instrument_ok': 'Yes',
    }

    if prefs:
        profile['preferred_type'] = prefs.lot_type or ''
        profile['min_roommate_age'] = str(prefs.minimumage) if prefs.minimumage is not None else '18'
        profile['max_roommate_age'] = str(prefs.maximumage) if prefs.maximumage is not None else '99'
        profile['city'] = prefs.city or ''
        profile['location_radius'] = str(prefs.locationmaxrange) if prefs.locationmaxrange is not None else ''
        if prefs.locationcoordlat is not None and prefs.locationcoordlon is not None:
            profile['preferred_location'] = f'{prefs.locationcoordlat},{prefs.locationcoordlon}'
        # When user has accommodation, preference "roommate has accommodation" is irrelevant → show nothing
        if up.hashousing:
            profile['roommate_has_accommodation'] = ''
        else:
            profile['roommate_has_accommodation'] = (prefs.hashousing or '').strip().lower() or ''
        profile['roommate_gender'] = "Doesn't matter" if (prefs.preferred_sex or '') == 'doesnt_matter' else (prefs.preferred_sex or "Doesn't matter")
        profile['roommate_pet_ok'] = (
            'Yes' if prefs.pets.exclude(value__iexact='no').exists() else 'No'
        ) if prefs.pets.exists() else 'Yes'
        profile['roommate_smoker_ok'] = prefs.smoker or 'No'
        profile['roommate_parties_ok'] = prefs.party or 'Yes'
        profile['roommate_partner_ok'] = prefs.partner or "Doesn't matter"
        profile['roommate_instrument_ok'] = (
            'Yes' if prefs.instruments.exclude(value__iexact='no').exists() else 'No'
        ) if prefs.instruments.exists() else 'Yes'
        profile['roommate_accommodation_type'] = prefs.lot_type or ''
        profile['roommate_party_frequency'] = prefs.party or ''
        profile['city_lat'] = str(prefs.locationcoordlat) if prefs.locationcoordlat is not None else ''
        profile['city_lon'] = str(prefs.locationcoordlon) if prefs.locationcoordlon is not None else ''
        profile['instruments_bother'] = ', '.join(
            i.value for i in prefs.instruments.exclude(value__iexact='yes').exclude(value__iexact='no')
        ) if prefs.instruments.exists() else ''
        profile['pets_not_wanted'] = ', '.join(
            p.value for p in prefs.pets.exclude(value__iexact='yes').exclude(value__iexact='no')
        ) if prefs.pets.exists() else ''

    # When user has their own accommodation, preferred type, city and radius are not applicable — show as —
    if up.hashousing:
        profile['preferred_type'] = ''
        profile['city'] = ''
        profile['location_radius'] = ''

    return profile


def _choice_value(raw, allowed, default=None):
    """Return normalized value if in allowed set, else default."""
    if not raw or not str(raw).strip():
        return default
    v = str(raw).strip().lower()
    return v if v in allowed else default


def _normalize_pet_or_instrument(raw):
    """Lowercase and trim (e.g. '  Guitar  ' -> 'guitar')."""
    if not raw or not str(raw).strip():
        return None
    return str(raw).strip().lower()


def _parse_comma_separated(raw, normalizer=_normalize_pet_or_instrument):
    """Split by comma, normalize each, return list of non-empty values."""
    if not raw or not str(raw).strip():
        return []
    return [
        normalizer(part)
        for part in str(raw).split(',')
        if normalizer(part)
    ]


def _get_or_create_pets_or_instruments(model, raw_string):
    """Get or create Preferencepet/Preferenceinstrument for each comma-separated value (lowercased)."""
    values = _parse_comma_separated(raw_string)
    objs = []
    for v in values:
        existing = model.objects.filter(value__iexact=v).first()
        if existing:
            objs.append(existing)
        else:
            objs.append(model.objects.create(value=v))
    return objs


def _parse_date_dd_mm_yyyy(s):
    """Parse date string dd.mm.yyyy to date."""
    if not s or not str(s).strip():
        return None
    try:
        return datetime.strptime(str(s).strip(), '%d.%m.%Y').date()
    except ValueError:
        return None


# Allowed image extensions for profile photos (lowercase)
_PROFILE_PHOTO_EXT_MAP = {
    'image/jpeg': 'jpg',
    'image/jpg': 'jpg',
    'image/png': 'png',
    'image/gif': 'gif',
    'image/webp': 'webp',
}


def _profile_photo_path(profile_id, uploaded_file):
    """
    Generate path for a profile photo. Stored under media/profile_pics/profile_{profile_id}.{ext}
    profile_id is the user/profile id (idacc); extension from content_type or filename; default jpg.
    """
    ext = _PROFILE_PHOTO_EXT_MAP.get((uploaded_file.content_type or '').strip().lower())
    if not ext and getattr(uploaded_file, 'name', None):
        raw = uploaded_file.name.rsplit('.', 1)[-1].strip().lower() if '.' in uploaded_file.name else ''
        if raw in _PROFILE_PHOTO_EXT_MAP.values():
            ext = raw
    ext = ext or 'jpg'
    return f'profile_pics/profile_{profile_id}.{ext}'


def _parse_lat_lon(s):
    """Parse 'lat, lon' or 'lat,lon' to (Decimal, Decimal) or (None, None)."""
    if not s or not str(s).strip():
        return None, None
    parts = str(s).replace(',', ' ').split()
    if len(parts) >= 2:
        try:
            return Decimal(parts[0]), Decimal(parts[1])
        except Exception:
            pass
    return None, None


def _geocode_city(city_name):
    """Get (lat, lon) for a city name via Nominatim (OpenStreetMap). Returns (Decimal, Decimal) or (None, None)."""
    if not city_name or not str(city_name).strip():
        return None, None
    city_clean = str(city_name).strip()
    headers = {'User-Agent': 'ZimmerRoommateApp/1.0 (contact@example.com)'}

    def _fetch(q):
        url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({
            'q': q,
            'format': 'json',
            'limit': 1,
        })
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json_loads(resp.read().decode())
            if data and len(data) > 0:
                item = data[0]
                lat = item.get('lat') or item.get('latitude')
                lon = item.get('lon') or item.get('lng') or item.get('longitude')
                if lat is not None and lon is not None:
                    return Decimal(str(lat)), Decimal(str(lon))
        return None, None

    try:
        result = _fetch(city_clean)
        if result[0] is not None and result[1] is not None:
            return result
        # Fallback: try with country suffix (e.g. "Belgrade, Serbia"); respect Nominatim 1 req/s
        time.sleep(1)
        result = _fetch(f'{city_clean}, Serbia')
        if result[0] is not None and result[1] is not None:
            return result
    except Exception:
        pass
    return None, None


# Validation: names/city = letters (and spaces, hyphens for names only)
_RE_NAME = re.compile(r'^[a-zA-Z\s\-]+$')
_RE_CITY = re.compile(r'^[a-zA-Z\s\-]+$')
_RE_PHONE = re.compile(r'^\+38\d{9,10}$')   # +38 then 9 or 10 digits
_RE_JMBG = re.compile(r'^\d{13}$')


def _validate_profile_form(data, files):
    """Validate required format; returns (None, None) if ok, else (context_dict, template)."""
    first_name = (data.get('first_name') or '').strip()
    last_name = (data.get('last_name') or '').strip()
    phone = (data.get('phone') or '').strip()
    id_number = (data.get('id_number') or '').strip()
    city = (data.get('city') or '').strip()
    occupation = (data.get('occupation') or '').strip()

    if not first_name or not _RE_NAME.match(first_name):
        return {'error': 'First name must contain only letters, spaces, or hyphens.'}, 'create_profile.html'
    if not last_name or not _RE_NAME.match(last_name):
        return {'error': 'Last name must contain only letters, spaces, or hyphens.'}, 'create_profile.html'
    if not phone or not _RE_PHONE.match(phone):
        return {'error': 'Phone must be +38 followed by 9 or 10 digits (e.g. +38912345678).'}, 'create_profile.html'
    if not id_number or not _RE_JMBG.match(id_number):
        return {'error': 'ID number (JMBG) must be exactly 13 digits.'}, 'create_profile.html'
    has_acc = (data.get('has_accommodation') or '').strip().lower() == 'yes'
    if not has_acc and (not city or not _RE_CITY.match(city)):
        return {'error': 'City must contain only letters, spaces, or hyphens.'}, 'create_profile.html'
    if occupation and not _RE_NAME.match(occupation):
        return {'error': 'Occupation must contain only letters, spaces, or hyphens.'}, 'create_profile.html'

    dob = _parse_date_dd_mm_yyyy(data.get('date_of_birth'))
    if not dob:
        return {'error': 'Invalid date of birth (use dd.mm.yyyy).'}, 'create_profile.html'
    if dob > date.today():
        return {'error': 'Date of birth cannot be in the future.'}, 'create_profile.html'
    age = (date.today() - dob).days // 365
    if age < 16:
        return {'error': 'You must be at least 16 years old.'}, 'create_profile.html'

    if not files.get('profile_photo'):
        return {'error': 'Profile photo is required.'}, 'create_profile.html'

    if not has_acc:
        budget_raw = (data.get('budget') or '').strip()
        if not budget_raw:
            return {'error': 'Budget (EUR) is required when you are looking for accommodation.'}, 'create_profile.html'
        try:
            b = Decimal(budget_raw)
            if b < 1:
                return {'error': 'Budget (EUR) must be greater than 0 when you are looking for accommodation.'}, 'create_profile.html'
        except Exception:
            return {'error': 'Budget (EUR) must be a valid number.'}, 'create_profile.html'

    if has_acc:
        rent_raw = (data.get('accommodation_rent') or '').strip()
        if not rent_raw:
            return {'error': 'Monthly rent for roommate (EUR) is required when you have accommodation.'}, 'create_profile.html'
        try:
            r = Decimal(rent_raw)
            if r < 1:
                return {'error': 'Monthly rent for roommate must be at least 1 EUR.'}, 'create_profile.html'
        except Exception:
            return {'error': 'Monthly rent for roommate must be a valid number.'}, 'create_profile.html'

    return None, None


def _validate_edit_profile_form(data):
    """Same rules as create profile (photo optional). Returns (None, None) if ok, else (error_section_id, error_message)."""
    first_name = (data.get('first_name') or '').strip()
    last_name = (data.get('last_name') or '').strip()
    phone = (data.get('phone') or '').strip()
    id_number = (data.get('id_number') or '').strip()
    city = (data.get('city') or '').strip()
    occupation = (data.get('occupation') or '').strip()

    if not first_name or not _RE_NAME.match(first_name):
        return 'validationMessageBasic', 'First name must contain only letters, spaces, or hyphens.'
    if not last_name or not _RE_NAME.match(last_name):
        return 'validationMessageBasic', 'Last name must contain only letters, spaces, or hyphens.'
    if not phone or not _RE_PHONE.match(phone):
        return 'validationMessageBasic', 'Phone must be +38 followed by 9 or 10 digits (e.g. +38912345678).'
    if not id_number or not _RE_JMBG.match(id_number):
        return 'validationMessageBasic', 'ID number (JMBG) must be exactly 13 digits.'
    has_acc = (data.get('has_accommodation') or '').strip().lower() == 'yes'
    if not has_acc and (not city or not _RE_CITY.match(city)):
        return 'validationMessageAccommodation', 'City must contain only letters, spaces, or hyphens.'
    if occupation and not _RE_NAME.match(occupation):
        return 'validationMessageBasic', 'Occupation must contain only letters, spaces, or hyphens.'

    dob = _parse_date_dd_mm_yyyy(data.get('date_of_birth'))
    if not dob:
        return 'validationMessageBasic', 'Invalid date of birth (use dd.mm.yyyy).'
    if dob > date.today():
        return 'validationMessageBasic', 'Date of birth cannot be in the future.'
    age = (date.today() - dob).days // 365
    if age < 16:
        return 'validationMessageBasic', 'You must be at least 16 years old.'

    if not has_acc:
        budget_raw = (data.get('budget') or '').strip()
        if not budget_raw:
            return 'validationMessageBasic', 'Budget (EUR) is required when you are looking for accommodation.'
        try:
            b = Decimal(budget_raw)
            if b < 1:
                return 'validationMessageBasic', 'Budget (EUR) must be greater than 0 when you are looking for accommodation.'
        except Exception:
            return 'validationMessageBasic', 'Budget (EUR) must be a valid number.'

    # About me
    gender = _choice_value((data.get('gender') or '').strip().lower(), SEX_VALUES)
    if not gender:
        return 'validationMessageAbout', 'Gender is required.'
    if has_acc:
        accommodation_type = _choice_value((data.get('accommodation_type') or '').strip().lower(), LOT_TYPE_VALUES)
        if not accommodation_type:
            return 'validationMessageAbout', 'Please select accommodation type (house or apartment).'
        rent_raw = (data.get('accommodation_rent') or data.get('roommate_rent') or '').strip()
        if not rent_raw:
            return 'validationMessageAbout', 'Monthly rent for roommate (EUR) is required when you have accommodation.'
        try:
            r = Decimal(rent_raw)
            if r < 1:
                return 'validationMessageAbout', 'Monthly rent for roommate must be at least 1 EUR.'
        except Exception:
            return 'validationMessageAbout', 'Monthly rent for roommate must be a valid number.'
    if (data.get('has_pet') or '').strip().lower() == 'yes' and not (data.get('pet_type') or '').strip():
        return 'validationMessageAbout', 'Please enter what pet you have.'
    if (data.get('has_parties') or '').strip().lower() == 'yes':
        party_freq = _choice_value((data.get('party_frequency') or 'no').strip().lower(), PARTY_VALUES)
        if not party_freq or party_freq == 'no':
            return 'validationMessageAbout', 'Please select how often you have parties.'
    if (data.get('plays_instrument') or '').strip().lower() == 'yes' and not (data.get('instrument_name') or '').strip():
        return 'validationMessageAbout', 'Please enter which instrument you play.'

    # Accommodation preferences (when no accommodation)
    if not has_acc:
        preferred = _choice_value((data.get('preferred_type') or '').strip().lower(), LOT_TYPE_PREF_VALUES)
        if not preferred:
            return 'validationMessageAccommodation', 'Please select preferred accommodation type.'

    return None, None


def _profile_dict_from_post(data, existing_profile=None):
    """Build profile dict from POST for re-rendering edit form on validation error. Matches keys expected by my_profile.html."""
    get = lambda k, d='': (data.get(k) or d) if data else d
    acc = (get('has_accommodation') or '').strip().lower() == 'yes'
    return {
        'profile_photo_url': existing_profile.get('profile_photo_url', '') if existing_profile else '',
        'first_name': get('first_name'),
        'last_name': get('last_name'),
        'date_of_birth': get('date_of_birth'),
        'id_number': get('id_number'),
        'phone': get('phone'),
        'occupation': get('occupation'),
        'budget': get('budget', '200'),
        'has_accommodation': 'Yes' if acc else 'No',
        'accommodation_address': get('accommodation_address'),
        'accommodation_type': (get('accommodation_type') or '').strip().lower(),
        'housing_rent': get('accommodation_rent') or get('roommate_rent'),
        'accommodation_lat': get('accommodation_lat'),
        'accommodation_lon': get('accommodation_lon'),
        'gender': (get('gender') or '').strip().lower(),
        'has_pet': 'Yes' if (get('has_pet') or '').strip().lower() == 'yes' else 'No',
        'pet_type': get('pet_type'),
        'smoker': (get('smoker') or 'no').strip().lower(),
        'has_parties': 'Yes' if (get('has_parties') or '').strip().lower() == 'yes' else 'No',
        'party_frequency': (get('party_frequency') or '').strip().lower(),
        'has_partner': (get('has_partner') or 'no').strip().lower(),
        'plays_instrument': 'Yes' if (get('plays_instrument') or '').strip().lower() == 'yes' else 'No',
        'instrument_name': get('instrument_name'),
        'preferred_type': (get('preferred_type') or '').strip().lower(),
        'min_roommate_age': get('min_roommate_age', '18'),
        'max_roommate_age': get('max_roommate_age', '65'),
        'city': get('city'),
        'preferred_location': get('preferred_location'),
        'location_radius': get('location_radius'),
        'roommate_has_accommodation': _choice_value((get('roommate_has_accommodation') or '').strip().lower(), ROOMMATE_HAS_ACCOMMODATION_PREF_VALUES, 'doesnt_matter') or '',
        'roommate_gender': (get('roommate_gender') or 'doesnt_matter').strip().lower(),
        'roommate_pet_ok': (get('roommate_pet_ok') or 'yes').strip().lower(),
        'roommate_smoker_ok': (get('roommate_smoker_ok') or 'no').strip().lower(),
        'roommate_parties_ok': (get('roommate_parties_ok') or 'yes').strip().lower(),
        'roommate_partner_ok': (get('roommate_partner_ok') or 'doesnt_matter').strip().lower(),
        'roommate_instrument_ok': (get('roommate_instrument_ok') or 'yes').strip().lower(),
        'roommate_accommodation_type': (get('roommate_accommodation_type') or '').strip().lower(),
        'roommate_party_frequency': (get('roommate_party_frequency') or '').strip().lower(),
        'city_lat': get('city_lat'),
        'city_lon': get('city_lon'),
        'instruments_bother': get('instruments_bother'),
        'pets_not_wanted': get('pets_not_wanted'),
    }


def _document_photo_path(db_id, file):
    """
    Generate path for ID document photo. Stored under media/documents/id_{db_id}.{ext}
    db_id is the id in the database (e.g. account id / idacc); extension from content_type or filename.
    """
    ext = _PROFILE_PHOTO_EXT_MAP.get((file.content_type or '').strip().lower())
    if not ext and getattr(file, 'name', None) and '.' in file.name:
        raw = file.name.rsplit('.', 1)[-1].strip().lower()
        if raw in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
            ext = raw
    ext = ext or 'jpg'
    return f'documents/id_{db_id}.{ext}'


def get_document_photo_path(account_id):
    """
    Return the stored document photo path for the given account ID,
    regardless of extension, or None if no file exists.
    """
    possible_extensions = ('jpg', 'jpeg', 'png', 'gif', 'webp')

    for ext in possible_extensions:
        path = f'documents/id_{account_id}.{ext}'
        if default_storage.exists(path):
            return path

    return None


@logged_out_required
@require_http_methods(['GET', 'POST'])
def register(request):
    """Handle sign-up: validate input, create account, redirect to create_profile. Author: Luka Rapaic 2022/0266."""
    if request.method != 'POST':
        return render(request, 'register.html')

    data = request.POST
    get = lambda key, default=None: data.get(key, default) or default

    email = get('email', '').strip()
    password = get('password', '')
    password_confirm = get('password_confirm', '')

    # ----- Validation -----

    if not email:
        return render(request, 'register.html', {'error': 'Email is required.'})

    if not password:
        return render(request, 'register.html', {'error': 'Password is required.'})

    if password != password_confirm:
        return render(request, 'register.html', {'error': 'Passwords do not match.'})

    if 'id_photo' not in request.FILES:
        return render(request, 'register.html', {'error': 'ID document photo is required.'})

    if Account.objects.filter(email=email).exists():
        return render(request, 'register.html', {'error': 'Email already exists.'})

    id_file = request.FILES['id_photo']
    saved_file_path = None

    try:
        with transaction.atomic():

            password_hash = hashlib.sha256(password.encode()).hexdigest()

            account = Account.objects.create(
                email=email,
                passwordhash=password_hash,
                status='ACTIVE'
            )

            saved_file_path = default_storage.save(
                _document_photo_path(account.idacc, id_file),
                id_file
            )

    except Exception:
        if saved_file_path:
            try:
                default_storage.delete(saved_file_path)
            except Exception:
                pass
        raise

    request.session['user_id'] = account.idacc
    request.session['user_email'] = account.email
    request.session['user_type'] = UserType.NEW_REGISTRATION.value

    return redirect('create_profile')

@logged_out_required
@require_http_methods(['GET', 'POST'])
def login(request):
    """Authenticate user, set session, redirect by role (moderator/create_profile/swipe). Author: Luka Rapaic 2022/0266."""
    if request.method != 'POST':
        return render(request, 'login.html')

    data = request.POST
    get = lambda key, default=None: data.get(key, default) or default

    email = get('email', '').strip()
    password = get('password', '').strip()

    if not email or not password:
        return render(request, 'login.html', {'error': 'Email and password are required.'})

    password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

    try:
        with transaction.atomic():
            try:
                user = Account.objects.get(email=email, passwordhash=password_hash, status='ACTIVE')
            except Account.DoesNotExist:
                return render(request, 'login.html', {'error': 'Invalid email or password.'})

            # ----- Determine user type -----
            if Moderator.objects.filter(idacc = user).exists():
                user_type = UserType.MODERATOR
            else:
                userProfile = UserProfile.objects.get(idacc = user)
                if not userProfile:
                    user_type = UserType.NEW_REGISTRATION
                elif not userProfile.isVerified:
                    user_type = UserType.UNVERIFIED
                else:
                    user_type = UserType.VERIFIED

            # ----- Store in session -----
            request.session['user_id'] = user.idacc
            request.session['user_email'] = user.email
            request.session['user_type'] = user_type.value

            # ----- Redirect based on type -----
            if user_type == UserType.MODERATOR:
                return redirect('moderator_page')
            elif user_type == UserType.NEW_REGISTRATION:
                return redirect('create_profile')
            else:
                return redirect('swipe')

    except Exception:
        return render(request, 'login.html', {'error': 'An unexpected error occurred. Please try again.'})


@login_required
def logout_view(request):
    """Clear session and redirect to home. Author: Luka Rapaic 2022/0266."""
    request.session.flush()
    return redirect('/')


@require_http_methods(['GET', 'POST'])
def moderator_verify(request):
    """Moderator page: list unverified accounts, verify or reject. GET shows list, POST performs action."""
    if request.method == 'POST':
        account_id = request.POST.get('account_id')
        action = request.POST.get('action')

        try:
            with transaction.atomic():
                entry = Unverifiedaccounts.objects.select_related('idacc').get(idacc=account_id)

                if action == 'approve':
                    profile = UserProfile.objects.select_related('idacc').get(idacc=account_id)
                    profile.isVerified = True
                    profile.save()

                # Just remove the unverified entry whether approved or rejected
                entry.delete()

        except Unverifiedaccounts.DoesNotExist:
            pass  # If entry doesn't exist, nothing to do

        return redirect('moderator_page')

    # ---- get next account waiting for verification ----
    entry = (
        Unverifiedaccounts.objects
        .select_related('idacc')
        .filter(idacc__userprofile__isnull=False)
        .first()
    )

    profile = None
    if entry:
        profile = UserProfile.objects.get(idacc=entry.idacc)

    return render(request, 'moderator_verify.html', {
        'entry': entry,
        'profile': profile,
        'media_url': settings.MEDIA_URL
    })


@login_required
@require_http_methods(['GET', 'POST'])
def create_profile(request):
    """First-time profile creation: validate form, save profile/preferences/housing, create unverified account. Authors: Jovana Ceganjac 2022/0423, Milica Eva Stojanovic 2022/0361."""
    if request.method != 'POST':
        return render(request, 'create_profile.html')

    data = request.POST
    get = lambda key, default=None: data.get(key, default) or default

    # ----- Validation (names, phone, JMBG, city, DOB, profile photo) -----
    err_ctx, err_tpl = _validate_profile_form(request.POST, request.FILES)
    if err_ctx is not None:
        return render(request, err_tpl, err_ctx)

    # ----- Enum-like fields: validate and use values directly -----
    sex_val = _choice_value(get('gender'), SEX_VALUES)
    if not sex_val:
        return render(request, 'create_profile.html', {'error': 'Gender is required.'})
    smoker_val = _choice_value(get('smoker', 'no'), SMOKER_VALUES, 'no')
    has_parties = get('has_parties', 'no') == 'yes'
    party_freq = _choice_value(get('party_frequency', 'no') if has_parties else 'no', PARTY_VALUES, 'no')
    partner_val = _choice_value(get('has_partner', 'no'), PARTNER_VALUES, 'no')

    has_accommodation = get('has_accommodation', 'no') == 'yes'
    accommodation_type = _choice_value(get('accommodation_type'), LOT_TYPE_VALUES) if has_accommodation else None

    pet_type_raw = get('pet_type') if get('has_pet') == 'yes' else ''
    profile_pets = _get_or_create_pets_or_instruments(Preferencepet, pet_type_raw)
    instrument_raw = get('instrument_name') if get('plays_instrument') == 'yes' else ''
    profile_instruments = _get_or_create_pets_or_instruments(Preferenceinstrument, instrument_raw)

    dob = _parse_date_dd_mm_yyyy(get('date_of_birth'))
    # When user has accommodation, budget is not used (stored as 0)
    if has_accommodation:
        budget = Decimal('0')
    else:
        budget_val = get('budget', '0')
        try:
            budget = Decimal(budget_val) if budget_val else Decimal('0')
        except Exception:
            budget = Decimal('0')

    preferred_sex_val = _choice_value(get('roommate_gender'), PREFERRED_SEX_VALUES, default='doesnt_matter')
    roommate_smoker = _choice_value(get('roommate_smoker_ok', 'no'), SMOKER_VALUES, 'no')
    roommate_party = get('roommate_parties_ok', 'no') == 'yes'
    roommate_party_freq = _choice_value(get('roommate_party_frequency', 'no') if roommate_party else 'no', PARTY_VALUES, 'no')
    roommate_partner = _choice_value(get('roommate_partner_ok', 'doesnt_matter'), PARTNER_PREF_VALUES, 'doesnt_matter')
    roommate_has_acc = None if has_accommodation else _choice_value(
        (get('roommate_has_accommodation') or '').strip().lower(),
        ROOMMATE_HAS_ACCOMMODATION_PREF_VALUES,
        'doesnt_matter'
    )
    pref_lot_type_val = _choice_value(get('roommate_accommodation_type'), LOT_TYPE_PREF_VALUES)
    if pref_lot_type_val == 'doesnt_matter':
        pref_lot_type_val = None
    min_age_val = get('min_roommate_age', '18')
    max_age_val = get('max_roommate_age', '65')
    try:
        min_age = int(min_age_val) if min_age_val else 18
    except ValueError:
        min_age = 18
    try:
        max_age = int(max_age_val) if max_age_val else 99
    except ValueError:
        max_age = 99
    # Coordinates: prefer map pin (Preferred location), then city lookup (city_lat/city_lon), then server geocode
    pref_lat, pref_lon = None, None
    preferred_loc = get('preferred_location', '').strip()
    if preferred_loc:
        pref_lat, pref_lon = _parse_lat_lon(preferred_loc)
    if pref_lat is None or pref_lon is None:
        city_lat_post = get('city_lat', '').strip()
        city_lon_post = get('city_lon', '').strip()
        if city_lat_post and city_lon_post:
            try:
                pref_lat, pref_lon = Decimal(city_lat_post), Decimal(city_lon_post)
            except Exception:
                pass
    if pref_lat is None or pref_lon is None:
        city_name = get('city', '').strip()
        city_lat, city_lon = _geocode_city(city_name)
        pref_lat, pref_lon = city_lat, city_lon
    radius_val = get('location_radius')
    if radius_val is not None and str(radius_val).strip() != '':
        try:
            locationmaxrange = Decimal(str(radius_val).strip())
        except Exception:
            locationmaxrange = Decimal('20')
    else:
        locationmaxrange = Decimal('20')

    # When user has accommodation: only UserPreferences nullable fields are left null (preferred type, location, radius).
    # Housing (lat, lon, rent, lot_type) is still inserted below from accommodation_* form fields.
    if has_accommodation:
        pref_lot_type_val = None
        pref_lat = None
        pref_lon = None
        locationmaxrange = None
    pets_not_wanted_raw = get('pets_not_wanted') if get('roommate_pet_ok') == 'no' else ''
    instruments_bother_raw = get('instruments_bother') if get('roommate_instrument_ok') == 'no' else ''

    # ----- Single transaction: account, profile, housing, preferences – roll back everything if any step fails -----
    saved_file_path = None
    try:
        with transaction.atomic():
            user_id = request.session.get('user_id')
            try:
                account = Account.objects.get(idacc=user_id)
            except Account.DoesNotExist:
                return render(request, 'create_profile.html', {'error': f'Account with id {user_id} does not exist. Create dummy accounts first.'})

            if UserProfile.objects.filter(idacc=account).exists():
                return render(request, 'create_profile.html', {'error': 'Profile already exists for this account.'})

            f = request.FILES['profile_photo']
            saved_file_path = default_storage.save(_profile_photo_path(account.idacc, f), f)

            profile = UserProfile.objects.create(
                idacc=account,
                jmbg=get('id_number', '').strip(),
                phonenumber=get('phone', '').strip(),
                name=get('first_name', '').strip(),
                surname=get('last_name', '').strip(),
                dateofbirth=dob,
                occupation=get('occupation') or None,
                budget=budget,
                hashousing=has_accommodation,
                lot_type=accommodation_type,
                profilephotourl=saved_file_path,
                sex=sex_val,
                smoker=smoker_val,
                party=party_freq,
                partner=partner_val,
            )
            profile.pets.set(profile_pets)
            profile.instruments.set(profile_instruments)

            if has_accommodation and accommodation_type:
                acc_lat = get('accommodation_lat')
                acc_lon = get('accommodation_lon')
                try:
                    housing_lat = Decimal(acc_lat) if acc_lat else None
                except Exception:
                    housing_lat = None
                try:
                    housing_lon = Decimal(acc_lon) if acc_lon else None
                except Exception:
                    housing_lon = None
                rent_val = get('accommodation_rent', '').strip()
                try:
                    rent = Decimal(rent_val) if rent_val else None
                except Exception:
                    rent = None
                if rent is None or rent < 1:
                    raise ValueError('Monthly rent for roommate is required and must be at least 1 EUR.')
                Housing.objects.create(
                    owneridacc=profile,
                    lot_type=accommodation_type,
                    rent=rent,
                    address=(get('accommodation_address', '') or '').strip() or None,
                    locationcoordlat=housing_lat,
                    locationcoordlon=housing_lon,
                )

            prefs_city = None if has_accommodation else (get('city', '') or '').strip() or None
            prefs = UserPreferences.objects.create(
                idacc=profile,
                preferred_sex=preferred_sex_val,
                smoker=roommate_smoker,
                party=roommate_party_freq,
                partner=roommate_partner,
                hashousing=roommate_has_acc,
                lot_type=pref_lot_type_val,
                minimumage=min_age,
                maximumage=max_age,
                city=prefs_city,
                locationcoordlat=pref_lat,
                locationcoordlon=pref_lon,
                locationmaxrange=locationmaxrange,
            )
            prefs.pets.set(_get_or_create_pets_or_instruments(Preferencepet, pets_not_wanted_raw))
            prefs.instruments.set(_get_or_create_pets_or_instruments(Preferenceinstrument, instruments_bother_raw))

            personal_document_path = get_document_photo_path(account.idacc)
            Unverifiedaccounts.objects.create(
                idacc=account,
                personaldocumentphoto=personal_document_path
            )
    except Exception:
        if saved_file_path:
            try:
                default_storage.delete(saved_file_path)
            except Exception:
                pass
        raise

    request.session['user_type'] = UserType.UNVERIFIED.value
    return redirect('swipe')


@profile_required
@ensure_csrf_cookie
def my_profile(request):
    """Show or edit current user profile. GET: render form with DB data. POST: validate and save; supports AJAX (returns JSON). Author: Jovana Ceganjac 2022/0423."""
    up = get_current_user_profile(request)
    if up is None:
        # No profile in DB: show empty fields so template does not break
        empty_profile = {k: '' for k in (
            'profile_photo_url', 'first_name', 'last_name', 'date_of_birth', 'id_number', 'phone',
            'occupation', 'budget', 'has_accommodation', 'accommodation_address', 'accommodation_type',
            'housing_rent', 'gender', 'has_pet', 'pet_type', 'smoker', 'has_parties', 'party_frequency', 'has_partner',
            'plays_instrument', 'instrument_name', 'preferred_type', 'min_roommate_age', 'max_roommate_age',
            'city', 'preferred_location', 'location_radius', 'roommate_has_accommodation', 'roommate_gender',
            'roommate_pet_ok', 'roommate_smoker_ok', 'roommate_parties_ok', 'roommate_partner_ok', 'roommate_instrument_ok',
        )}
        return render(request, 'my_profile.html', {'profile': empty_profile})

    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        # Validate with same rules as create (profile photo optional on edit)
        err_section, err_message = _validate_edit_profile_form(request.POST)
        if err_section is not None:
            if is_ajax:
                return JsonResponse({
                    'ok': False,
                    'error': err_message,
                    'error_section': err_section,
                })
            prefs = getattr(up, 'userpreferences', None)
            housing = Housing.objects.filter(owneridacc=up).first()
            current_profile = profile_to_context(up, prefs, housing, request)
            profile_from_post = _profile_dict_from_post(request.POST, current_profile)
            return render(request, 'my_profile.html', {
                'profile': profile_from_post,
                'error': err_message,
                'error_section': err_section,
                'show_edit_form': True,
            })

        prefs = getattr(up, 'userpreferences', None)
        housing = Housing.objects.filter(owneridacc=up).first()

        # Read-only fields (from hidden inputs)
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        date_of_birth_str = request.POST.get('date_of_birth', '').strip()
        id_number = request.POST.get('id_number', '').strip()
        phone = request.POST.get('phone', '').strip()

        # Editable fields
        occupation = request.POST.get('occupation', '').strip() or None
        budget_raw = request.POST.get('budget', '0').strip()
        try:
            budget = Decimal(budget_raw) if budget_raw else Decimal('0')
        except (InvalidOperation, ValueError):
            budget = Decimal('0')

        has_accommodation = (request.POST.get('has_accommodation', '').strip().lower() == 'yes')
        accommodation_type = request.POST.get('accommodation_type', '').strip().lower() or None
        gender_val = request.POST.get('gender', '').strip().lower() or None
        has_pet = (request.POST.get('has_pet', '').strip().lower() == 'yes')
        smoker = (request.POST.get('smoker', '').strip().lower() == 'yes')
        has_parties = (request.POST.get('has_parties', '').strip().lower() == 'yes')
        has_partner = (request.POST.get('has_partner', '').strip().lower() == 'yes')
        plays_instrument = (request.POST.get('plays_instrument', '').strip().lower() == 'yes')

        # Roommate preferences
        # When user has accommodation, preference is irrelevant → save null
        roommate_has_accommodation_raw = request.POST.get('roommate_has_accommodation', '').strip().lower() if not has_accommodation else ''
        roommate_has_accommodation = _choice_value(roommate_has_accommodation_raw, ROOMMATE_HAS_ACCOMMODATION_PREF_VALUES, 'doesnt_matter') if roommate_has_accommodation_raw else None
        if has_accommodation:
            roommate_has_accommodation = None
        roommate_gender_val = request.POST.get('roommate_gender', '').strip().lower()
        if roommate_gender_val in ('doesnt_matter', "doesn't matter", ''):
            roommate_gender_val = None
        min_age_raw = request.POST.get('min_roommate_age', '18').strip()
        max_age_raw = request.POST.get('max_roommate_age', '99').strip()
        try:
            min_age = int(min_age_raw) if min_age_raw else 18
        except ValueError:
            min_age = 18
        try:
            max_age = int(max_age_raw) if max_age_raw else 99
        except ValueError:
            max_age = 99
        preferred_location_str = request.POST.get('preferred_location', '').strip()
        location_radius_raw = request.POST.get('location_radius', '').strip()
        try:
            location_radius = Decimal(location_radius_raw) if location_radius_raw else None
        except (InvalidOperation, ValueError):
            location_radius = None

        preferred_type_single = (request.POST.get('preferred_type') or '').strip().lower()
        party_freq = _choice_value(request.POST.get('party_frequency', 'no').strip().lower(), PARTY_VALUES, 'no')
        lot_type_profile = _choice_value(accommodation_type, LOT_TYPE_VALUES) if (has_accommodation and accommodation_type) else None

        # Parse date (d.m.Y)
        dateofbirth = up.dateofbirth
        if date_of_birth_str:
            try:
                dateofbirth = datetime.strptime(date_of_birth_str, '%d.%m.%Y').date()
            except ValueError:
                pass

        # Update UserProfile (enum fields: sex, smoker, party, partner, lot_type)
        up.name = first_name or up.name
        up.surname = last_name or up.surname
        up.dateofbirth = dateofbirth
        up.jmbg = id_number or up.jmbg
        up.phonenumber = phone or up.phonenumber
        up.occupation = occupation
        up.budget = budget
        up.hashousing = has_accommodation
        up.lot_type = lot_type_profile
        up.sex = _choice_value(gender_val, SEX_VALUES, 'other')
        up.smoker = 'yes' if smoker else 'no'
        up.party = party_freq
        up.partner = 'yes' if has_partner else 'no'
        up.save()
        # Profile pets/instruments: same as create – comma-separated, get_or_create each, set M2M (replaces previous)
        pet_type_raw = request.POST.get('pet_type', '') if has_pet else ''
        instrument_raw = request.POST.get('instrument_name', '') if plays_instrument else ''
        up.pets.set(_get_or_create_pets_or_instruments(Preferencepet, pet_type_raw))
        up.instruments.set(_get_or_create_pets_or_instruments(Preferenceinstrument, instrument_raw))

        # Profile photo: optional on edit. If no new file is uploaded, keep existing photo and do not re-verify.
        profile_photo_file = request.FILES.get('profile_photo')
        if profile_photo_file:
            allowed = ('image/jpeg', 'image/png', 'image/webp', 'image/gif')
            if profile_photo_file.content_type in allowed and profile_photo_file.size < 10 * 1024 * 1024:  # 10 MB
                old_path = up.profilephotourl
                saved_path = default_storage.save(_profile_photo_path(up.idacc_id, profile_photo_file), profile_photo_file)
                up.profilephotourl = saved_path
                # TODO Add account to unverified accounts
                # up.isverified = False  # must be verified again after photo change
                up.save(update_fields=['profilephotourl'])
                if old_path and old_path != saved_path:
                    try:
                        default_storage.delete(old_path)
                    except Exception:
                        pass

        # UserPreferences: update or create (enum fields)
        pref_lot = _choice_value(preferred_type_single, LOT_TYPE_PREF_VALUES) if preferred_type_single else None
        roommate_pet = (request.POST.get('roommate_pet_ok', '').strip().lower() == 'yes')
        roommate_smoker = (request.POST.get('roommate_smoker_ok', '').strip().lower() == 'yes')
        roommate_parties = (request.POST.get('roommate_parties_ok', '').strip().lower() == 'yes')
        roommate_partner_val = (request.POST.get('roommate_partner_ok', '').strip().lower())
        roommate_partner_val = _choice_value(roommate_partner_val, PARTNER_PREF_VALUES, 'doesnt_matter')
        roommate_party_freq = _choice_value(request.POST.get('roommate_party_frequency', 'no'), PARTY_VALUES, 'no')
        roommate_instrument = (request.POST.get('roommate_instrument_ok', '').strip().lower() == 'yes')
        pets_not_wanted_raw = request.POST.get('pets_not_wanted', '') if not roommate_pet else ''
        instruments_bother_raw = request.POST.get('instruments_bother', '') if not roommate_instrument else ''

        loc_lat = loc_lon = None
        if preferred_location_str:
            parts = [p.strip() for p in preferred_location_str.replace(',', ' ').split()]
            if len(parts) >= 2:
                try:
                    loc_lat = Decimal(parts[0])
                    loc_lon = Decimal(parts[1])
                except (InvalidOperation, ValueError):
                    pass

        # When user has accommodation: only UserPreferences nullable fields are left null.
        # Housing (lat, lon, rent, lot_type, address) is still saved below from accommodation_* form fields.
        city_for_prefs = None
        if has_accommodation:
            pref_lot = None
            loc_lat = None
            loc_lon = None
            location_radius = None
        else:
            city_for_prefs = (request.POST.get('city', '') or '').strip() or None

        if prefs is None:
            prefs = UserPreferences(idacc=up)
        prefs.preferred_sex = _choice_value(roommate_gender_val, PREFERRED_SEX_VALUES, 'doesnt_matter') if roommate_gender_val else 'doesnt_matter'
        prefs.smoker = 'yes' if roommate_smoker else 'no'
        prefs.party = roommate_party_freq
        prefs.partner = roommate_partner_val
        prefs.hashousing = roommate_has_accommodation
        prefs.lot_type = pref_lot
        prefs.minimumage = min_age
        prefs.maximumage = max_age
        prefs.city = city_for_prefs
        prefs.locationcoordlat = loc_lat
        prefs.locationcoordlon = loc_lon
        prefs.locationmaxrange = location_radius
        prefs.save()
        prefs.pets.set(_get_or_create_pets_or_instruments(Preferencepet, pets_not_wanted_raw))
        prefs.instruments.set(_get_or_create_pets_or_instruments(Preferenceinstrument, instruments_bother_raw))

        # Housing: create/update when has accommodation; delete and clear profile accommodation fields when no longer has accommodation
        if has_accommodation:
            lot_type_housing = _choice_value(accommodation_type, LOT_TYPE_VALUES) or 'apartment'
            rent_raw = (request.POST.get('accommodation_rent') or request.POST.get('roommate_rent') or '0').strip()
            try:
                rent = Decimal(rent_raw) if rent_raw else Decimal('0')
            except (InvalidOperation, ValueError):
                rent = Decimal('0')
            if housing is None:
                housing = Housing(owneridacc=up, lot_type=lot_type_housing, rent=rent)
            else:
                housing.lot_type = lot_type_housing
                housing.rent = rent
            housing.address = (request.POST.get('accommodation_address') or '').strip() or None
            acc_lat_raw = (request.POST.get('accommodation_lat') or '').strip()
            acc_lon_raw = (request.POST.get('accommodation_lon') or '').strip()
            try:
                housing.locationcoordlat = Decimal(acc_lat_raw) if acc_lat_raw else None
                housing.locationcoordlon = Decimal(acc_lon_raw) if acc_lon_raw else None
            except (InvalidOperation, ValueError, TypeError):
                housing.locationcoordlat = None
                housing.locationcoordlon = None
            housing.save()
        else:
            if housing:
                housing.delete()

        if is_ajax:
            return JsonResponse({
                'ok': True,
                'redirect_url': reverse('my_profile'),
            })
        return redirect('my_profile')

    # GET: load from DB
    prefs = getattr(up, 'userpreferences', None)
    housing = Housing.objects.filter(owneridacc=up).first()
    profile = profile_to_context(up, prefs, housing, request)
    return render(request, 'my_profile.html', {'profile': profile, 'can_delete': True})


@profile_required
def delete_profile(request):
    """Delete current user's profile and account (POST only). Removes preferences, housing, swipes, matches. Author: Jovana Ceganjac 2022/0423."""
    if request.method != 'POST':
        return redirect('my_profile')
    up = get_current_user_profile(request)
    if up is None:
        return redirect('my_profile')

    account = up.idacc
    # Eksplicitno obrisi sve povezano pre naloga
    prefs = getattr(up, 'userpreferences', None)
    if prefs is not None:
        prefs.pets.clear()
        prefs.instruments.clear()
        prefs.delete()
    Housing.objects.filter(owneridacc=up).delete()
    up.pets.clear()
    up.instruments.clear()
    up.delete()
    account.delete()

    # After deleting the account/profile, also log the user out
    request.session.flush()

    try:
        from django.contrib import messages
        messages.success(request, 'Your profile has been deleted.')
    except Exception:
        pass
    return redirect('home')


DEFAULT_PROXIMITY_KM = 20  # default search radius when user has accommodation (no prefs radius)
BUDGET_LENIENCY = Decimal('70')    # max ±70 so budgets / rent are in a similar range
BUDGET_MAX_ABOVE_VIEWER = Decimal('70')   # don't show if housing rent (or their budget) is more than viewer's budget + this
SUGGESTIONS_MAX = 500  # return all suggestions in one load (no load-more; seamless swipe)
MAX_PROXIMITY_KM = 50


def _normalize_text(value):
    """Normalize text for comparisons."""
    return (value or '').strip().lower()


def _safe_decimal(value):
    """Convert value to Decimal if possible, else return None."""
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _user_has_housing(profile, housing):
    """True only when profile says they have housing and a Housing row exists."""
    return bool(profile and profile.hashousing and housing)


def _effective_budget_amount(profile, housing):
    """
    Amount used for affordability comparison.
    - If user has housing and rent exists, use rent.
    - Otherwise use profile budget.
    """
    if profile.hashousing and housing and housing.rent is not None:
        return housing.rent
    return profile.budget


def _effective_lot_type(profile, housing):
    """
    Effective accommodation type.
    Prefer profile.lot_type, otherwise housing.lot_type, otherwise empty string.
    """
    return _normalize_text(
        profile.lot_type or (housing.lot_type if housing else None) or ''
    )


def _pet_values(profile):
    """All pet values linked to a profile."""
    return set(profile.pets.values_list('value', flat=True))


def _instrument_values(profile):
    """All instrument values linked to a profile."""
    return set(profile.instruments.values_list('value', flat=True))


def _actual_pet_values(profile):
    """Only real pet values, excluding control values."""
    return _pet_values(profile) - {'yes', 'no'}


def _actual_instrument_values(profile):
    """Only real instrument values, excluding control values."""
    return _instrument_values(profile) - {'yes', 'no'}


def _party_index(value):
    """Map party value to ordered index."""
    party_order = ('no', 'rarely', 'often', 'very_often')
    value = _normalize_text(value)
    return party_order.index(value) if value in party_order else 0


def _get_user_prefs(profile):
    """Return profile.userpreferences or None if missing."""
    if not profile:
        return None
    try:
        return profile.userpreferences
    except UserPreferences.DoesNotExist:
        return None


def _get_viewer_center_and_radius(viewer_profile, viewer_prefs, viewer_housing):
    """
    Return (lat, lon, radius_km) for the viewer's search circle.

    Rules:
    - If viewer has accommodation and housing coordinates, center on that housing.
    - Otherwise, if viewer preferences contain preferred coordinates, use those.
    - If no coordinates exist, return (None, None, None).
    """
    if (
            viewer_profile.hashousing
            and viewer_housing
            and viewer_housing.locationcoordlat is not None
            and viewer_housing.locationcoordlon is not None
    ):
        return (
            float(viewer_housing.locationcoordlat),
            float(viewer_housing.locationcoordlon),
            float(DEFAULT_PROXIMITY_KM),
        )

    if (
            viewer_prefs
            and viewer_prefs.locationcoordlat is not None
            and viewer_prefs.locationcoordlon is not None
    ):
        raw_radius = viewer_prefs.locationmaxrange
        radius_km = float(raw_radius) if raw_radius is not None and raw_radius > 0 else float(DEFAULT_PROXIMITY_KM)
        return (
            float(viewer_prefs.locationcoordlat),
            float(viewer_prefs.locationcoordlon),
            radius_km,
        )

    return None, None, None


def _get_candidate_location(candidate_profile, candidate_prefs, candidate_housing):
    """
    Return candidate location used for proximity checks.

    Rules:
    - If candidate has accommodation, use housing coordinates.
    - Otherwise, use preferred location from preferences.
    """
    if (
            candidate_profile.hashousing
            and candidate_housing
            and candidate_housing.locationcoordlat is not None
            and candidate_housing.locationcoordlon is not None
    ):
        return float(candidate_housing.locationcoordlat), float(candidate_housing.locationcoordlon)

    if (
            candidate_prefs
            and candidate_prefs.locationcoordlat is not None
            and candidate_prefs.locationcoordlon is not None
    ):
        return float(candidate_prefs.locationcoordlat), float(candidate_prefs.locationcoordlon)

    return None, None


def _get_candidate_radius_km(candidate_prefs):
    """Return candidate radius if available, otherwise None."""
    if not candidate_prefs or candidate_prefs.locationmaxrange is None:
        return None

    try:
        radius = float(candidate_prefs.locationmaxrange)
        return radius if radius > 0 else float(DEFAULT_PROXIMITY_KM)
    except (TypeError, ValueError):
        return None


def _haversine_km(lat1, lon1, lat2, lon2):
    """Return distance in km between two coordinate pairs."""
    if None in (lat1, lon1, lat2, lon2):
        return None

    try:
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
    except (TypeError, ValueError):
        return None

    earth_radius_km = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(min(1, a)))
    return earth_radius_km * c


def _within_proximity(
        viewer_profile,
        viewer_prefs,
        viewer_housing,
        candidate_profile,
        candidate_prefs,
        candidate_housing,
        use_max_distance = False
):
    """
    True if candidate is acceptable by location.

    Behavior preserved:
    - If viewer has no usable coordinates, proximity does not filter anything.
    - If viewer has accommodation:
        - candidate must NOT have accommodation
        - candidate preferred location must fall inside viewer circle
        - if candidate location is missing, pass leniently
    - If viewer does not have accommodation:
        - if candidate has accommodation, candidate housing must be inside viewer circle
        - if candidate also lacks accommodation, circles must overlap
        - if candidate location is missing, pass leniently
    """
    viewer_lat, viewer_lon, viewer_radius = _get_viewer_center_and_radius(
        viewer_profile,
        viewer_prefs,
        viewer_housing,
    )
    if use_max_distance:
        viewer_radius = float(MAX_PROXIMITY_KM)

    if viewer_lat is None or viewer_radius is None:
        return True

    if viewer_profile.hashousing:
        if candidate_profile.hashousing:
            return False

        candidate_lat, candidate_lon = _get_candidate_location(
            candidate_profile,
            candidate_prefs,
            candidate_housing,
        )
        candidate_radius = float(MAX_PROXIMITY_KM) if use_max_distance else _get_candidate_radius_km(candidate_prefs)

        if candidate_lat is None:
            return True

        distance = _haversine_km(viewer_lat, viewer_lon, candidate_lat, candidate_lon)
        return distance is not None and distance <= candidate_radius

    candidate_lat, candidate_lon = _get_candidate_location(
        candidate_profile,
        candidate_prefs,
        candidate_housing,
    )

    if candidate_lat is None:
        return True

    distance = _haversine_km(viewer_lat, viewer_lon, candidate_lat, candidate_lon)
    if distance is None:
        return True

    if candidate_profile.hashousing:
        return distance <= viewer_radius

    candidate_radius = float(MAX_PROXIMITY_KM) if use_max_distance else _get_candidate_radius_km(candidate_prefs)
    if candidate_radius is None:
        candidate_radius = float(DEFAULT_PROXIMITY_KM)

    return distance <= viewer_radius + candidate_radius


def _preferences_match(
        viewer_profile,
        viewer_prefs,
        viewer_housing,
        candidate_profile,
        candidate_prefs,
        candidate_housing,
):
    """
    Return True if viewer and candidate satisfy the full preference rules.

    Behavior intentionally preserved exactly, including lenient handling and asymmetries
    in the original implementation.
    """

    # ------------------------------------------------------------------
    # Budget / affordability
    # ------------------------------------------------------------------
    viewer_amount = _effective_budget_amount(viewer_profile, viewer_housing)
    candidate_amount = _effective_budget_amount(candidate_profile, candidate_housing)

    if viewer_amount is not None and candidate_amount is not None:
        try:
            viewer_money = Decimal(str(viewer_amount))
            candidate_money = Decimal(str(candidate_amount))

            if viewer_money == 0 and candidate_money == 0:
                pass
            elif viewer_money == 0 or candidate_money == 0:
                pass
            else:
                if abs(viewer_money - candidate_money) > BUDGET_LENIENCY:
                    return False
                if candidate_money > viewer_money + BUDGET_MAX_ABOVE_VIEWER:
                    return False
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Roommate has accommodation
    # ------------------------------------------------------------------
    if viewer_prefs is not None and viewer_prefs.hashousing:
        viewer_housing_pref = _normalize_text(viewer_prefs.hashousing)
        candidate_has_housing = bool(candidate_profile.hashousing)

        if viewer_housing_pref == 'yes' and not candidate_has_housing:
            return False
        if viewer_housing_pref == 'no' and candidate_has_housing:
            return False

    if candidate_prefs is not None and candidate_prefs.hashousing:
        candidate_housing_pref = _normalize_text(candidate_prefs.hashousing)
        viewer_has_housing = bool(viewer_profile.hashousing)

        if candidate_housing_pref == 'yes' and not viewer_has_housing:
            return False
        if candidate_housing_pref == 'no' and viewer_has_housing:
            return False

    # ------------------------------------------------------------------
    # Lot type
    # ------------------------------------------------------------------
    if viewer_prefs and viewer_prefs.lot_type:
        viewer_lot_pref = _normalize_text(viewer_prefs.lot_type)
        if viewer_lot_pref not in ('anyways', 'doesnt_matter', ''):
            candidate_lot_type = None
            if candidate_profile.hashousing:
                candidate_lot_type = _effective_lot_type(candidate_profile, candidate_housing)
            if candidate_lot_type and candidate_lot_type != viewer_lot_pref:
                return False

    if candidate_prefs and candidate_prefs.lot_type and viewer_profile.hashousing:
        candidate_lot_pref = _normalize_text(candidate_prefs.lot_type)
        if candidate_lot_pref not in ('anyways', 'doesnt_matter', ''):
            viewer_lot_type = _effective_lot_type(viewer_profile, viewer_housing)
            if viewer_lot_type and viewer_lot_type != candidate_lot_pref:
                return False

    # ------------------------------------------------------------------
    # Pets
    # prefs.pets = pets they do not want
    # ------------------------------------------------------------------
    if viewer_prefs:
        viewer_pet_prefs = set(viewer_prefs.pets.values_list('value', flat=True))

        if 'no' in viewer_pet_prefs:
            candidate_pet_values = set(candidate_profile.pets.values_list('value', flat=True)) - {'no'}
            if candidate_pet_values:
                return False

        viewer_disliked_pets = viewer_pet_prefs - {'yes', 'no'}
        if viewer_disliked_pets:
            candidate_pets = _actual_pet_values(candidate_profile)
            if candidate_pets & viewer_disliked_pets:
                return False

    if candidate_prefs:
        candidate_pet_prefs = set(candidate_prefs.pets.values_list('value', flat=True))

        if 'no' in candidate_pet_prefs:
            viewer_pet_values = set(viewer_profile.pets.values_list('value', flat=True)) - {'no'}
            if viewer_pet_values:
                return False

        candidate_disliked_pets = candidate_pet_prefs - {'yes', 'no'}
        if candidate_disliked_pets:
            viewer_pets = _actual_pet_values(viewer_profile)
            if viewer_pets & candidate_disliked_pets:
                return False

    # ------------------------------------------------------------------
    # Instruments
    # prefs.instruments = instruments that bother them
    # ------------------------------------------------------------------
    if viewer_prefs:
        viewer_bothered_by = set(viewer_prefs.instruments.values_list('value', flat=True)) - {'yes', 'no'}
        if viewer_bothered_by:
            candidate_plays = _actual_instrument_values(candidate_profile)
            if candidate_plays & viewer_bothered_by:
                return False

    if candidate_prefs:
        candidate_bothered_by = set(candidate_prefs.instruments.values_list('value', flat=True)) - {'yes', 'no'}
        if candidate_bothered_by:
            viewer_plays = _actual_instrument_values(viewer_profile)
            if viewer_plays & candidate_bothered_by:
                return False

    # ------------------------------------------------------------------
    # Preferred sex
    # ------------------------------------------------------------------
    if (
            viewer_prefs
            and viewer_prefs.preferred_sex
            and _normalize_text(viewer_prefs.preferred_sex) != 'doesnt_matter'
    ):
        if _normalize_text(candidate_profile.sex) != _normalize_text(viewer_prefs.preferred_sex):
            return False

    if (
            candidate_prefs
            and candidate_prefs.preferred_sex
            and _normalize_text(candidate_prefs.preferred_sex) != 'doesnt_matter'
    ):
        if _normalize_text(viewer_profile.sex) != _normalize_text(candidate_prefs.preferred_sex):
            return False

    # ------------------------------------------------------------------
    # Partner
    # NOTE: behavior preserved exactly: only viewer preference is checked here.
    # ------------------------------------------------------------------
    if (
            viewer_prefs
            and viewer_prefs.partner
            and _normalize_text(viewer_prefs.partner) != 'doesnt_matter'
    ):
        if _normalize_text(candidate_profile.partner) != _normalize_text(viewer_prefs.partner):
            return False

    # ------------------------------------------------------------------
    # Party
    # ------------------------------------------------------------------
    if viewer_prefs and viewer_prefs.party:
        viewer_party_pref = _normalize_text(viewer_prefs.party or 'no')
        if viewer_party_pref not in ('often', 'very_often'):
            candidate_party = _normalize_text(candidate_profile.party or 'no')
            try:
                viewer_index = _party_index(viewer_party_pref)
                candidate_index = _party_index(candidate_party)
                if candidate_index > viewer_index + 1:
                    return False
            except ValueError:
                pass

    if candidate_prefs and candidate_prefs.party:
        candidate_party_pref = _normalize_text(candidate_prefs.party or 'no')
        if candidate_party_pref not in ('often', 'very_often'):
            viewer_party = _normalize_text(viewer_profile.party or 'no')
            try:
                candidate_index = _party_index(candidate_party_pref)
                viewer_index = _party_index(viewer_party)
                if viewer_index > candidate_index + 1:
                    return False
            except ValueError:
                pass

    # ------------------------------------------------------------------
    # Smoker
    # ------------------------------------------------------------------
    if viewer_prefs and viewer_prefs.smoker:
        viewer_allows_smoker = _normalize_text(viewer_prefs.smoker) == 'yes'
        candidate_is_smoker = _normalize_text(candidate_profile.smoker) == 'yes'
        if not viewer_allows_smoker and candidate_is_smoker:
            return False

    if candidate_prefs and candidate_prefs.smoker:
        candidate_allows_smoker = _normalize_text(candidate_prefs.smoker) == 'yes'
        viewer_is_smoker = _normalize_text(viewer_profile.smoker) == 'yes'
        if not candidate_allows_smoker and viewer_is_smoker:
            return False

    # ------------------------------------------------------------------
    # Age
    # ------------------------------------------------------------------
    if (
            viewer_prefs
            and viewer_prefs.minimumage is not None
            and viewer_prefs.maximumage is not None
    ):
        candidate_age = _calculate_age(candidate_profile.dateofbirth)
        if candidate_age is not None:
            if candidate_age < viewer_prefs.minimumage or candidate_age > viewer_prefs.maximumage:
                return False

    if (
            candidate_prefs
            and candidate_prefs.minimumage is not None
            and candidate_prefs.maximumage is not None
    ):
        viewer_age = _calculate_age(viewer_profile.dateofbirth)
        if viewer_age is not None:
            if viewer_age < candidate_prefs.minimumage or viewer_age > candidate_prefs.maximumage:
                return False

    return True


def _passes_budget(viewer_profile, viewer_housing, candidate_profile, candidate_housing):
    """Budget-only version of the same affordability rules."""
    viewer_amount = _effective_budget_amount(viewer_profile, viewer_housing)
    candidate_amount = _effective_budget_amount(candidate_profile, candidate_housing)

    if viewer_amount is None or candidate_amount is None:
        return True

    try:
        viewer_money = Decimal(str(viewer_amount))
        candidate_money = Decimal(str(candidate_amount))

        if viewer_money == 0 and candidate_money == 0:
            return True
        if viewer_money == 0 or candidate_money == 0:
            return True
        if abs(viewer_money - candidate_money) > BUDGET_LENIENCY:
            return False
        if candidate_money > viewer_money + BUDGET_MAX_ABOVE_VIEWER:
            return False
    except Exception:
        pass

    return True


def _passes_strict_dealbreakers(viewer_profile, viewer_prefs, candidate_profile, candidate_prefs):
    """
    Strict fallback filter only.

    Strict dealbreakers:
    - preferred sex
    - hasHousing
    - age
    - smoker
    """

    # ----- preferred sex -----
    if viewer_prefs and viewer_prefs.preferred_sex:
        viewer_pref_sex = _normalize_text(viewer_prefs.preferred_sex)
        if viewer_pref_sex != 'doesnt_matter':
            candidate_sex = _normalize_text(candidate_profile.sex)
            if candidate_sex != viewer_pref_sex:
                return False

    if candidate_prefs and candidate_prefs.preferred_sex:
        candidate_pref_sex = _normalize_text(candidate_prefs.preferred_sex)
        if candidate_pref_sex != 'doesnt_matter':
            viewer_sex = _normalize_text(viewer_profile.sex)
            if viewer_sex != candidate_pref_sex:
                return False

    # ----- hasHousing -----
    if viewer_prefs and viewer_prefs.hashousing:
        viewer_housing_pref = _normalize_text(viewer_prefs.hashousing)
        candidate_has_housing = bool(candidate_profile.hashousing)

        if viewer_housing_pref == 'yes' and not candidate_has_housing:
            return False
        if viewer_housing_pref == 'no' and candidate_has_housing:
            return False

    if candidate_prefs and candidate_prefs.hashousing:
        candidate_housing_pref = _normalize_text(candidate_prefs.hashousing)
        viewer_has_housing = bool(viewer_profile.hashousing)

        if candidate_housing_pref == 'yes' and not viewer_has_housing:
            return False
        if candidate_housing_pref == 'no' and viewer_has_housing:
            return False

    # ----- age -----
    if viewer_prefs and viewer_prefs.minimumage is not None and viewer_prefs.maximumage is not None:
        candidate_age = _calculate_age(candidate_profile.dateofbirth)
        if candidate_age is not None:
            if candidate_age < viewer_prefs.minimumage or candidate_age > viewer_prefs.maximumage:
                return False

    if candidate_prefs and candidate_prefs.minimumage is not None and candidate_prefs.maximumage is not None:
        viewer_age = _calculate_age(viewer_profile.dateofbirth)
        if viewer_age is not None:
            if viewer_age < candidate_prefs.minimumage or viewer_age > candidate_prefs.maximumage:
                return False

    # ----- smoker -----
    if viewer_prefs and _normalize_text(viewer_prefs.smoker):
        viewer_allows_smoker = _normalize_text(viewer_prefs.smoker) == 'yes'
        candidate_is_smoker = _normalize_text(candidate_profile.smoker) == 'yes'
        if not viewer_allows_smoker and candidate_is_smoker:
            return False

    if candidate_prefs and _normalize_text(candidate_prefs.smoker):
        candidate_allows_smoker = _normalize_text(candidate_prefs.smoker) == 'yes'
        viewer_is_smoker = _normalize_text(viewer_profile.smoker) == 'yes'
        if not candidate_allows_smoker and viewer_is_smoker:
            return False

    return True


def get_suggested_roommates(viewer_profile):
    """
    Return suggested roommates for the viewer.

    Flow:
    1. Exclude self and already-swiped profiles.
    2. Try full match: proximity + full preferences.
    3. If empty, try fallback: strict deal-breakers + proximity + budget.
    4. If still empty, try strict deal-breakers only.
    """
    if not viewer_profile:
        return []

    viewer_id = viewer_profile.idacc_id
    viewer_prefs = _get_user_prefs(viewer_profile)
    viewer_housing = Housing.objects.filter(owneridacc=viewer_profile).first()

    already_swiped_ids = set(
        Swipes.objects.filter(idkor1_id=viewer_id).values_list('idkor2_id', flat=True)
    )

    candidates_qs = (
        UserProfile.objects
        .filter(isVerified=True)
        .exclude(idacc_id=viewer_id)
        .exclude(idacc_id__in=already_swiped_ids)
        .order_by('idacc_id')
        .prefetch_related(
            'pets',
            'instruments',
            'userpreferences',
            'userpreferences__pets',
            'userpreferences__instruments',
        )
    )

    candidates = list(candidates_qs)
    candidate_ids = [candidate.idacc_id for candidate in candidates]

    housing_by_owner_id = {
        housing.owneridacc_id: housing
        for housing in Housing.objects.filter(owneridacc_id__in=candidate_ids)
    }

    suggestions = []

    for candidate in candidates:
        if len(suggestions) >= SUGGESTIONS_MAX:
            break

        candidate_prefs = _get_user_prefs(candidate)
        candidate_housing = housing_by_owner_id.get(candidate.idacc_id)

        if not _within_proximity(
                viewer_profile,
                viewer_prefs,
                viewer_housing,
                candidate,
                candidate_prefs,
                candidate_housing,
        ):
            continue

        if not _preferences_match(
                viewer_profile,
                viewer_prefs,
                viewer_housing,
                candidate,
                candidate_prefs,
                candidate_housing,
        ):
            continue

        suggestions.append(candidate)

    if not suggestions and candidates:
        for candidate in candidates:
            if len(suggestions) >= SUGGESTIONS_MAX:
                break

            candidate_prefs = _get_user_prefs(candidate)
            candidate_housing = housing_by_owner_id.get(candidate.idacc_id)

            if not _passes_strict_dealbreakers(viewer_profile, viewer_prefs, candidate, candidate_prefs):
                continue

            if not _within_proximity(
                    viewer_profile,
                    viewer_prefs,
                    viewer_housing,
                    candidate,
                    candidate_prefs,
                    candidate_housing,
            ):
                continue

            if not _passes_budget(viewer_profile, viewer_housing, candidate, candidate_housing):
                continue

            suggestions.append(candidate)

    if not suggestions and candidates:
        for candidate in candidates:
            if len(suggestions) >= SUGGESTIONS_MAX:
                break

            candidate_prefs = _get_user_prefs(candidate)
            candidate_housing = housing_by_owner_id.get(candidate.idacc_id)

            if not _passes_strict_dealbreakers(viewer_profile, viewer_prefs, candidate, candidate_prefs):
                continue

            if not _within_proximity(
                    viewer_profile,
                    viewer_prefs,
                    viewer_housing,
                    candidate,
                    candidate_prefs,
                    candidate_housing,
                    True
            ):
                continue

            suggestions.append(candidate)

    return suggestions


def _calculate_age(date_of_birth):
    if not date_of_birth:
        return None

    today = date.today()
    return (
        today.year
        - date_of_birth.year
        - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
    )


def _format_money(value):
    if value is None:
        return "€0"
    try:
        return f"€{int(value)}" if value == int(value) else f"€{value}"
    except Exception:
        return f"€{value}"


# First-caps display for swipe card (aligned with display_filters.format_display)
_SWIPE_DISPLAY_MAP = {
    'yes': 'Yes', 'no': 'No', 'male': 'Male', 'female': 'Female', 'other': 'Other',
    'house': 'House', 'apartment': 'Apartment', 'anyways': 'Anyway',
    'rarely': 'Rarely', 'often': 'Often', 'very_often': 'Very often',
    'doesnt_matter': "Doesn't matter", "doesn't matter": "Doesn't matter",
}


def _format_display_for_card(value):
    """Return display-ready text: first caps, known map, else title-case. Empty → em dash."""
    if value is None:
        return '\u2014'
    s = str(value).strip()
    if not s:
        return '\u2014'
    key = s.lower()
    if key in _SWIPE_DISPLAY_MAP:
        return _SWIPE_DISPLAY_MAP[key]
    if s.replace('.', '').replace(',', '').replace('-', '').isdigit() or (s and s[0].isdigit()):
        return s
    return s.replace('_', ' ').title()


def _viewer_coords(viewer_profile):
    """Return (lat, lon) for viewer from housing or preferences, or None."""
    if not viewer_profile:
        return None, None
    housing = Housing.objects.filter(owneridacc=viewer_profile).first()
    if housing and housing.locationcoordlat is not None and housing.locationcoordlon is not None:
        return float(housing.locationcoordlat), float(housing.locationcoordlon)
    prefs = getattr(viewer_profile, 'userpreferences', None)
    if prefs and prefs.locationcoordlat is not None and prefs.locationcoordlon is not None:
        return float(prefs.locationcoordlat), float(prefs.locationcoordlon)
    return None, None


def _profile_to_swipe_card(profile, viewer_profile=None):
    """Build a dict for one swipe card (id, name, image, budget, etc.). Returns None if profile is None."""
    if not profile:
        return None
    try:
        return _profile_to_swipe_card_impl(profile, viewer_profile)
    except Exception:
        # Never drop a suggested profile: return minimal card so user still sees them
        return {
            "id": getattr(profile, 'idacc_id', 0),
            "firstName": (getattr(profile, 'name', None) or "").strip() or "\u2014",
            "lastName": (getattr(profile, 'surname', None) or "").strip() or "\u2014",
            "age": _calculate_age(getattr(profile, 'dateofbirth', None)),
            "status": "—",
            "gender": "",
            "image": static('img/default-profile.png'),
            "matched": False,
            "hasAccommodation": False,
            "housingStatus": "needs_housing",
            "housingLabel": "Needs Housing",
            "budgetValue": None,
            "rentValue": None,
            "locationLine": "\u2014",
            "address": None,
            "preferredCity": None,
            "lifestyle": [],
            "pets": [],
            "instruments": [],
            "accommodationLat": None,
            "accommodationLon": None,
        }


def _profile_to_swipe_card_impl(profile, viewer_profile=None):
    housing = Housing.objects.filter(owneridacc=profile).first()
    has_acc = bool(profile.hashousing and housing)
    prefs = _get_user_prefs(profile)

    # Identity
    occupation = (profile.occupation or "").strip()
    status = occupation.capitalize() if occupation else "No occupation"
    gender = _format_display_for_card(getattr(profile, "sex", None))
    if gender == '\u2014':
        gender = ""

    # Housing block (critical: needs vs offers)
    if has_acc:
        housing_status = "offers_housing"
        lot_type = (profile.lot_type or (housing.lot_type if housing else '') or '').lower()
        housing_label = "Offers " + _format_display_for_card(lot_type) if lot_type else "Offers accommodation"
        rent_value = _format_money(housing.rent)
        address = (housing.address or '').strip() or ''
        city = address.rsplit(',', 1)[-1].strip() if (address and ',' in address) else address or ''
        location_line = address if address else city or '\u2014'
        budget_value = None
        preferred_city = None
        accommodation_lat = float(housing.locationcoordlat) if housing and housing.locationcoordlat is not None else None
        accommodation_lon = float(housing.locationcoordlon) if housing and housing.locationcoordlon is not None else None
    else:
        housing_status = "needs_housing"
        housing_label = "Needs Housing"
        budget_value = _format_money(profile.budget)
        rent_value = None
        address = None
        preferred_city = (prefs.city or '').strip() if prefs else ''
        location_line = preferred_city or '\u2014'
        accommodation_lat = float(prefs.locationcoordlat) if prefs and prefs.locationcoordlat is not None else None
        accommodation_lon = float(prefs.locationcoordlon) if prefs and prefs.locationcoordlon is not None else None

    # Lifestyle: only non-empty, with natural phrasing for the card
    def _lifestyle_phrase(label, raw):
        val = _format_display_for_card(raw)
        if not val or val == '\u2014':
            return None
        v = (raw or '').strip().lower()
        if label == "Smoking":
            return "Non-smoker" if v == "no" else "Smoker"
        if label == "Parties":
            if v == "no":
                return "No parties"
            if v == "rarely":
                return "Rarely parties"
            if v == "often":
                return "Often parties"
            if v == "very_often":
                return "Very often parties"
            return val + " parties"
        if label == "Partner":
            return "No partner" if v == "no" else "Has partner"
        return label + ": " + val

    lifestyle = []
    for label, raw in [("Smoking", getattr(profile, "smoker", None)), ("Parties", getattr(profile, "party", None)), ("Partner", getattr(profile, "partner", None))]:
        phrase = _lifestyle_phrase(label, raw)
        if phrase:
            lifestyle.append({"display": phrase})

    # Interests: only non-empty lists (defensive: prefetch may be missing in some code paths)
    try:
        pets_raw = list(profile.pets.values_list('value', flat=True))
        instruments_raw = list(profile.instruments.values_list('value', flat=True))
    except Exception:
        pets_raw = []
        instruments_raw = []
    pets_list = [_format_display_for_card(p) for p in pets_raw if _format_display_for_card(p) != '\u2014']
    instruments_list = [_format_display_for_card(i) for i in instruments_raw if _format_display_for_card(i) != '\u2014']

    image_url = profile.profilephotourl
    if image_url and not image_url.startswith('/'):
        image_url = settings.MEDIA_URL + image_url
    elif not image_url:
        image_url = static('img/default-profile.png')

    return {
        "id": profile.idacc_id,
        "firstName": (profile.name or "").strip() or "\u2014",
        "lastName": (profile.surname or "").strip() or "\u2014",
        "age": _calculate_age(profile.dateofbirth),
        "status": status,
        "gender": gender,
        "image": image_url or "",
        "matched": False,
        "hasAccommodation": has_acc,
        "housingStatus": housing_status,
        "housingLabel": housing_label,
        "budgetValue": budget_value,
        "rentValue": rent_value,
        "locationLine": location_line,
        "address": address,
        "preferredCity": preferred_city or None,
        "lifestyle": lifestyle,
        "pets": pets_list,
        "instruments": instruments_list,
        "accommodationLat": accommodation_lat,
        "accommodationLon": accommodation_lon,
    }

@profile_required
def swipe(request):
    """Swipe page: show suggested roommate cards for verified user. Renders template with profiles or empty state. Authors: Maja Spirto 2022/0572, Milica Eva Stojanovic 2022/0361."""
    viewer = get_current_user_profile(request)
    if not viewer:
        return render(request, 'swipe.html', {'profiles_json': [], 'has_profiles': False, 'waiting_verification': False})

    waiting_verification = not viewer.isVerified
    suggested = get_suggested_roommates(viewer) if viewer.isVerified else []
    profiles = []
    for profile in suggested:
        try:
            card = _profile_to_swipe_card(profile, viewer)
            if card:
                profiles.append(card)
        except Exception:
            continue

    return render(request, 'swipe.html', {
        'profiles_json': profiles,
        'has_profiles': len(profiles) > 0,
        'waiting_verification': waiting_verification,
    })


@profile_required
def swipe_suggestions(request):
    """GET: return suggested roommates as JSON for load-more. Authors: Maja Spirto 2022/0572, Milica Eva Stojanovic 2022/0361."""
    viewer = get_current_user_profile(request)
    if not viewer:
        return JsonResponse({"profiles": []}, status=401)
    suggested = get_suggested_roommates(viewer)
    profiles = []
    for profile in suggested:
        try:
            card = _profile_to_swipe_card(profile, viewer)
            if card:
                profiles.append(card)
        except Exception:
            continue
    return JsonResponse({"profiles": profiles})


@profile_required
@require_http_methods(["POST"])
def swipe_action(request):
    """Record like/reject swipe; create match if mutual like. POST: target_id, decision. Authors: Maja Spirto 2022/0572, Milica Eva Stojanovic 2022/0361."""
    viewer = get_current_user_profile(request)
    if not viewer:
        return JsonResponse({"ok": False, "error": "not_authenticated"}, status=401)

    try:
        if request.content_type and "application/json" in request.content_type:
            body = json_loads(request.body or "{}")
            target_id = int(body.get("target_id"))
            decision = (body.get("decision") or "").strip().lower()
        else:
            target_id = int(request.POST.get("target_id"))
            decision = (request.POST.get("decision") or "").strip().lower()
    except (ValueError, TypeError, KeyError):
        return JsonResponse({"ok": False, "error": "invalid_params"}, status=400)

    if decision not in ("like", "reject"):
        return JsonResponse({"ok": False, "error": "invalid_params"}, status=400)

    viewer_id = viewer.idacc_id
    if target_id == viewer_id:
        return JsonResponse({"ok": False, "error": "invalid_params"}, status=400)

    candidate = UserProfile.objects.filter(idacc_id=target_id).first()
    if not candidate:
        return JsonResponse({"ok": False, "error": "user_not_found"}, status=404)

    with transaction.atomic():
        Swipes.objects.update_or_create(
            idkor1_id=viewer_id,
            idkor2_id=target_id,
            defaults={"decision": "LIKE" if decision == "like" else "DISLIKE"},
        )
        matched = False
        if decision == "like":
            other_swipe = (
                Swipes.objects
                .filter(
                    idkor1_id=target_id,
                    idkor2_id=viewer_id,
                    decision="LIKE",
                )
                .first()
            )
            if other_swipe:
                id1, id2 = min(viewer_id, target_id), max(viewer_id, target_id)
                Matches.objects.get_or_create(idkor1_id=id1, idkor2_id=id2)
                matched = True

    return JsonResponse({"ok": True, "matched": matched})


def _profile_to_match_card(profile):
    """Build a dict for matches list (id, full_name, age, email, phone, image)."""
    image_url = profile.profilephotourl
    if image_url:
        if not image_url.startswith('/'):
            image_url = settings.MEDIA_URL + image_url
    else:
        image_url = static('img/default-profile.png')

    return {
        "id": profile.idacc_id,
        "full_name": f"{profile.name} {profile.surname}",
        "age": _calculate_age(profile.dateofbirth),
        "email": profile.idacc.email if profile.idacc else "",
        "phone": profile.phonenumber or "",
        "image": image_url,
    }


@profile_required
def matches(request):
    """List mutual matches (users who both swiped like). Author: Maja Spirto 2022/0572."""
    current_user = get_current_user_profile(request)

    if current_user is None:
        return render(request, 'matches.html', {
            'matched_users': []
        })

    rows = (
        Matches.objects
        .filter(Q(idkor1=current_user) | Q(idkor2=current_user))
        .select_related('idkor1__idacc', 'idkor2__idacc')
    )

    matched_users = []
    seen_ids = set()

    for row in rows:
        if row.idkor1_id == current_user.idacc_id:
            other = row.idkor2
        else:
            other = row.idkor1

        if other.idacc_id in seen_ids:
            continue

        seen_ids.add(other.idacc_id)
        matched_users.append(_profile_to_match_card(other))

    return render(request, 'matches.html', {
        'matched_users': matched_users
    })


@profile_required
def remove_match(request, user_id):
    """Remove match with given user (POST). Author: Maja Spirto 2022/0572."""
    if request.method != "POST":
        return redirect('matches')

    current_user = get_current_user_profile(request)

    if current_user is None:
        return redirect('home')

    match = Matches.objects.filter(
        idkor1_id=current_user.idacc_id,
        idkor2_id=user_id
    ).first()

    if not match:
        match = Matches.objects.filter(
            idkor1_id=user_id,
            idkor2_id=current_user.idacc_id
        ).first()

    if match:
        match.delete()

    Swipes.objects.filter(
        idkor1_id=current_user.idacc_id,
        idkor2_id=user_id
    ).delete()

    return redirect('matches')


def home(request):
    """Landing page. Author: Maja Spirto 2022/0572."""
    is_moderator = False
    if request.session.get('user_id') and request.session.get('user_type') == UserType.MODERATOR.value:
        is_moderator = True
    return render(request, 'home.html', {'is_moderator': is_moderator})

