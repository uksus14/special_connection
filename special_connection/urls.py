"""
URL configuration for special_connection project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from special_connection.views import *
from django.urls import path, include

urlpatterns = [
    # path('admin/', admin.site.urls),
    # path('force', force),
    path('', entry),
    path('login', login_endpoint, name='login'),
    path('logout', logout_endpoint, name='logout'),
    path('render', render, name='render'),
    path('toggle', toggle, name='toggle'),
    path('hacks/', include('hacks.urls'), name='hacks'),
    path('current/', include('current.urls'), name='current'),
    path('time-machine/', include('time_machine.urls'), name='time_machine'),
    path('editor/', include('editor.urls'), name='editor'),
]
