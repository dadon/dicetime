from django.urls import path
from dice_time.settings import API_TOKEN
from . import views

urlpatterns = [
    # path('update/', views.update),
    path('tg/' + API_TOKEN, views.tg_webhook),
    path('tg2/' + API_TOKEN, views.tg_webhook_celery),
    path('username_select2/', views.UsernameSelect2Autocomplete.as_view(), name='username_select2'),
]
