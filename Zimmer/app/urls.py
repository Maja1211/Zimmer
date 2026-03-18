"""
Zimmer app URL config.
Authors: Jovana Ceganjac 2022/0423, Milica Eva Stojanovic 2022/0361, Maja Spirto 2022/0572, Luka Rapaic 2022/0266
"""
from django.contrib import admin
from django.urls import path
from .views import *

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', home, name='home'),
    path('register/', register, name='register'),
    path('login/', login, name="login"),
    path('logout/', logout_view, name='logout'),
    path('moderator/', moderator_verify, name='moderator_page'),
    path('create-profile/', create_profile, name='create_profile'),
    path('my-profile/', my_profile, name='my_profile'),
    path('my-profile/delete/', delete_profile, name='delete_profile'),
    path('swipe/', swipe, name='swipe'),
    path('swipe/suggestions/', swipe_suggestions, name='swipe_suggestions'),
    path('swipe-action/', swipe_action, name='swipe_action'),
    path('matches/', matches, name='matches'),
    path('remove-match/<int:user_id>/', remove_match, name='remove_match'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
