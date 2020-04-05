from django.urls import path
from dice_time.settings import API_TOKEN
from . import views

urlpatterns = [
    path('tg/' + API_TOKEN, views.tg_webhook),
    path('username_select2/', views.UsernameSelect2Autocomplete.as_view(), name='username_select2'),
]
