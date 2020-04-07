import logging

from django.urls import path
from dice_time.settings import API_TOKEN, LOCAL, ORIGIN
from . import views
from .tools import log_setup

urlpatterns = [
    # path('update/', views.update),
    path('tg/' + API_TOKEN, views.tg_webhook),
    path('username_select2/', views.UsernameSelect2Autocomplete.as_view(), name='username_select2'),
]

log_setup(logging.DEBUG)
