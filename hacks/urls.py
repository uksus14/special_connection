from hacks.views import *
from django.urls import path, include

urlpatterns = [
    path('', home, name='hacks'),
    path('profile/', include('user_profile.urls'), name='profile'),
    path('images/', include('images.urls'), name='images'),
]