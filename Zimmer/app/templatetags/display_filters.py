"""Template filters for displaying profile values: capitalised, no underscores, null as em dash."""
from django import template

register = template.Library()

# Map stored/raw values to display text (grammatically correct, capitalised, no underscores)
DISPLAY_MAP = {
    'yes': 'Yes',
    'no': 'No',
    'male': 'Male',
    'female': 'Female',
    'other': 'Other',
    'house': 'House',
    'apartment': 'Apartment',
    'anyways': 'Anyway',
    'rarely': 'Rarely',
    'often': 'Often',
    'very_often': 'Very often',
    'doesnt_matter': "Doesn't matter",
    "doesn't matter": "Doesn't matter",
}

EM_DASH = '\u2014'  # —


@register.filter
def format_display(value):
    """
    Format a profile value for display: null/empty → "—", known values → proper label, else title-case and replace _.
    """
    if value is None:
        return EM_DASH
    s = str(value).strip()
    if not s:
        return EM_DASH
    key = s.lower()
    if key in DISPLAY_MAP:
        return DISPLAY_MAP[key]
    # Numbers and coordinates: return as-is
    if s.replace('.', '').replace(',', '').replace('-', '').isdigit() or (s and s[0].isdigit()):
        return s
    # Replace underscores with spaces and title-case (e.g. "some_value" -> "Some value")
    return s.replace('_', ' ').title()
