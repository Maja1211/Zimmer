"""
Django models for Zimmer app (roommate matching).
Authors: Jovana Ceganjac 2022/0423, Milica Eva Stojanovic 2022/0361, Maja Spirto 2022/0572, Luka Rapaic 2022/0266
"""
from django.db import models

SEX_VALUES = ('male', 'female', 'other')
PREFERRED_SEX_VALUES = ('male', 'female', 'doesnt_matter')
SMOKER_VALUES = ('yes', 'no')
PARTY_VALUES = ('no', 'rarely', 'often', 'very_often')
PARTNER_VALUES = ('yes', 'no')
PARTNER_PREF_VALUES = ('yes', 'no', 'doesnt_matter')
LOT_TYPE_VALUES = ('house', 'apartment')
LOT_TYPE_PREF_VALUES = ('house', 'apartment', 'anyways', 'doesnt_matter')
# Preference: should the roommate have accommodation? (null when user has accommodation – irrelevant)
ROOMMATE_HAS_ACCOMMODATION_PREF_VALUES = ('yes', 'no', 'doesnt_matter') 


class Account(models.Model):
    """User account (email, password). One per user; links to profile or moderator."""
    idacc = models.AutoField(db_column='IdAcc', primary_key=True)
    email = models.CharField(db_column='Email', unique=True, max_length=255)
    passwordhash = models.CharField(db_column='PasswordHash', max_length=255)
    status = models.CharField(
        db_column='Status',
        max_length=7,
        choices=[('ACTIVE', 'ACTIVE'), ('DELETED', 'DELETED')],
        default='ACTIVE'
    )

    class Meta:
        managed = True
        db_table = 'account'

    def __str__(self):
        return self.email


class Moderator(models.Model):
    """Moderator role; extends Account."""
    idacc = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        db_column='IdAcc',
        primary_key=True
    )

    class Meta:
        managed = True
        db_table = 'moderator'


class Unverifiedaccounts(models.Model):
    """Account pending verification; stores document photo path."""
    idacc = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        db_column='IdAcc',
        primary_key=True
    )
    personaldocumentphoto = models.CharField(db_column='PersonalDocumentPhoto', max_length=255)

    class Meta:
        managed = True
        db_table = 'unverifiedaccounts'


class Preferencepet(models.Model):
    """Lookup: pet type value (e.g. dog, cat, no)."""
    idprefpet = models.AutoField(db_column='IdPrefPet', primary_key=True)
    value = models.CharField(db_column='Value', unique=True, max_length=50)

    class Meta:
        managed = True
        db_table = 'preferencepet'

    def __str__(self):
        return self.value


class Preferenceinstrument(models.Model):
    """Lookup: instrument name (e.g. guitar, no)."""
    idprefinstrument = models.AutoField(db_column='IdPrefInstrument', primary_key=True)
    value = models.CharField(db_column='Value', unique=True, max_length=50)

    class Meta:
        managed = True
        db_table = 'preferenceinstrument'

    def __str__(self):
        return self.value


class UserProfile(models.Model):
    """User profile: personal data, budget, housing flag, habits, pets/instruments."""
    idacc = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        db_column='IdAcc',
        primary_key=True
    )
    jmbg = models.CharField(db_column='JMBG', unique=True, max_length=13)
    phonenumber = models.CharField(db_column='PhoneNumber', max_length=20)
    name = models.CharField(db_column='Name', max_length=100)
    surname = models.CharField(db_column='Surname', max_length=100)
    dateofbirth = models.DateField(db_column='DateOfBirth')
    occupation = models.CharField(db_column='Occupation', max_length=100, blank=True, null=True)
    budget = models.DecimalField(db_column='Budget', max_digits=10, decimal_places=2, default=0)
    isVerified = models.BooleanField(db_column="isVerified", default=False)
    hashousing = models.BooleanField(db_column='HasHousing', default=False)
    lot_type = models.CharField(
        db_column='LotType',
        max_length=20,
        choices=[(x, x) for x in LOT_TYPE_VALUES],
        blank=True,
        null=True,
        help_text='house/apartment when has accommodation',
    )

    profilephotourl = models.CharField(db_column='ProfilePhotoUrl', max_length=255, blank=True, null=True)

    sex = models.CharField(db_column='Sex', max_length=20, choices=[(x, x) for x in SEX_VALUES], default='other')
    smoker = models.CharField(db_column='Smoker', max_length=10, choices=[(x, x) for x in SMOKER_VALUES], default='no')
    party = models.CharField(db_column='Party', max_length=20, choices=[(x, x) for x in PARTY_VALUES], default='no')
    partner = models.CharField(db_column='Partner', max_length=10, choices=[(x, x) for x in PARTNER_VALUES], default='no')

    pets = models.ManyToManyField(
        Preferencepet,
        blank=True,
        related_name='user_profiles'
    )
    instruments = models.ManyToManyField(
        Preferenceinstrument,
        blank=True,
        related_name='user_profiles'
    )

    class Meta:
        managed = True
        db_table = 'user_profile'

    def __str__(self):
        return f"{self.name} {self.surname} ({self.idacc_id})"


class UserPreferences(models.Model):
    """Preferences for roommate search: age range, location, pet/instrument preferences, etc."""
    idacc = models.OneToOneField(
        UserProfile,
        on_delete=models.CASCADE,
        db_column='IdAcc',
        primary_key=True
    )

    preferred_sex = models.CharField(
        db_column='PreferredSex',
        max_length=20,
        choices=[(x, x) for x in PREFERRED_SEX_VALUES],
        default='doesnt_matter',
    ) 
    smoker = models.CharField(db_column='Smoker', max_length=10, choices=[(x, x) for x in SMOKER_VALUES], default='no')
    party = models.CharField(db_column='Party', max_length=20, choices=[(x, x) for x in PARTY_VALUES], default='no')
    partner = models.CharField(db_column='Partner', max_length=20, choices=[(x, x) for x in PARTNER_PREF_VALUES], default='doesnt_matter')

    pets = models.ManyToManyField(
        Preferencepet,
        blank=True,
        related_name='user_preferences'
    )
    instruments = models.ManyToManyField(
        Preferenceinstrument,
        blank=True,
        related_name='user_preferences'
    )

    # yes/no/doesnt_matter; null when user has accommodation (preference not applicable)
    hashousing = models.CharField(
        db_column='HasHousing',
        max_length=20,
        choices=[(x, x) for x in ROOMMATE_HAS_ACCOMMODATION_PREF_VALUES],
        blank=True,
        null=True,
    )
    lot_type = models.CharField(
        db_column='LotType',
        max_length=20,
        choices=[(x, x) for x in LOT_TYPE_PREF_VALUES],
        blank=True,
        null=True,
    )

    minimumage = models.IntegerField(db_column='MinimumAge', default=18)
    maximumage = models.IntegerField(db_column='MaximumAge', default=99)

    locationcoordlat = models.DecimalField(
        db_column='LocationCoordLat',
        max_digits=10,
        decimal_places=8,
        blank=True,
        null=True
    )
    locationcoordlon = models.DecimalField(
        db_column='LocationCoordLon',
        max_digits=11,
        decimal_places=8,
        blank=True,
        null=True
    )
    locationmaxrange = models.DecimalField(
        db_column='LocationMaxRange',
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    city = models.CharField(db_column='City', max_length=200, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'user_preferences'

    def __str__(self):
        return f"Preferences for {self.idacc}"


class Housing(models.Model):
    """Accommodation offered by a user: address, rent, coordinates."""
    idhou = models.AutoField(db_column='IdHou', primary_key=True)
    owneridacc = models.ForeignKey(UserProfile, on_delete=models.CASCADE, db_column='OwnerIdAcc')
    lot_type = models.CharField(db_column='LotType', max_length=20, choices=[(x, x) for x in LOT_TYPE_VALUES], default='apartment')
    rent = models.DecimalField(db_column='Rent', max_digits=10, decimal_places=2)
    address = models.CharField(db_column='Address', max_length=255, blank=True, null=True)
    locationcoordlat = models.DecimalField(db_column='LocationCoordLat', max_digits=10, decimal_places=8, blank=True, null=True)
    locationcoordlon = models.DecimalField(db_column='LocationCoordLon', max_digits=11, decimal_places=8, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'housing'


class Swipes(models.Model):
    """Record of a swipe: user idkor1 swiped on idkor2 with LIKE or DISLIKE."""
    idswipe = models.AutoField(db_column='IdSwipe', primary_key=True)
    idkor1 = models.ForeignKey(UserProfile, on_delete=models.CASCADE, db_column='IdKor1', related_name='swipes_sent')
    idkor2 = models.ForeignKey(UserProfile, on_delete=models.CASCADE, db_column='IdKor2', related_name='swipes_received')
    decision = models.CharField(
        db_column='Decision',
        max_length=7,
        choices=[('LIKE', 'LIKE'), ('DISLIKE', 'DISLIKE')]
    )

    class Meta:
        managed = True
        db_table = 'swipes'
        unique_together = (('idkor1', 'idkor2'),)


class Matches(models.Model):
    """Mutual like: both users swiped LIKE on each other."""
    idmatch = models.AutoField(db_column='IdMatch', primary_key=True)
    idkor1 = models.ForeignKey(UserProfile, on_delete=models.CASCADE, db_column='IdKor1', related_name='matches_as_1')
    idkor2 = models.ForeignKey(UserProfile, on_delete=models.CASCADE, db_column='IdKor2', related_name='matches_as_2')

    class Meta:
        managed = True
        db_table = 'matches'
        unique_together = (('idkor1', 'idkor2'),)