from time_machine.views import *
from django.urls import path

urlpatterns = [
    path('', home, name='tm_home'),
    path('changes', home_changes, name='tm_home_changes'),
    path('downtimes', home_downtimes, name='tm_home_downtimes'),
    path('<int:pk>-<slug:index>.md', markdown, name='tm_markdown'),
    path('<int:pk>-<slug:index>.md/changes', markdown_changes, name='tm_changes'),
    path('<int:pk>-<slug:index>.md/downtimes', markdown_downtimes, name='tm_markdown_downtimes'),
]
