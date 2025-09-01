from django.urls import path
from current.views import *

urlpatterns = [
    path('', home, name='c_home'),
    path('<int:pk>-<slug:index>.md', markdown, name='c_markdown'),
    path('put', create_md, name='create')
]