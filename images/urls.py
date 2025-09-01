from django.urls import path
from images.views import *

urlpatterns = [
    path('', home, name='images'),
    path('temporary', temporary, name='temporary'),
    path('<str:name>', image, name='image'),
    path('<str:name>/save', save, name='save_image'),
    path('<str:name>/rename', rename, name='rename_image'),
    path('<str:name>/toggle-active', toggle_active, name='toggle_active'),
]