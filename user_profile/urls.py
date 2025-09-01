from user_profile.views import *
from django.urls import path

urlpatterns = [
    path('', profile, name='profile'),
    path('recolor', recolor, name='recolor'),
    path('rename', rename, name='rename'),
]