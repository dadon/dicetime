from django.urls import path
from . import views

urlpatterns = [
    path('username_select2/', views.UsernameSelect2Autocomplete.as_view(), name='username_select2'),
]
