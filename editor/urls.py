from django.urls import path
from editor.views import *

urlpatterns = [
    path('', home, name='e_home'),
    path('<int:pk>-<slug:index>.md', markdown, name='e_markdown'),
]
