from django.contrib import admin
from django import forms
from dal import autocomplete

from .models import *

"""
class IdForm(forms.ModelForm):
    user = forms.ModelChoiceField(
            queryset=User.objects.all(),
            widget=autocomplete.ModelSelect2(url='id_select2')
            )

    class Meta:
        model = Exceptions
        fields = ('__all__')

class WalletForm(forms.ModelForm):
    number = forms.ModelChoiceField(
            queryset=MinterWallets.objects.all(),
            widget=autocomplete.ModelSelect2(url='wallet_select2')
            )

    class Meta:
        model = Exceptions
        fields = ('__all__')
"""

@admin.register(Exceptions)
class ExceptionsAdmin(admin.ModelAdmin):
    #form = WalletForm
    list_display = ('user',)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):

    list_display = ('id', 'first_name', 'last_name', 'username')

    search_fields = ['id', 'first_name', 'last_name', 'username']


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):

    list_display = ('name',)

    search_fields = ['name']


@admin.register(MinterWallets)
class PrizmWalletAdmin(admin.ModelAdmin):

    list_display = ('user', 'number',)

    search_fields = ['user', 'number']


@admin.register(Triggers)
class TriggersAdmin(admin.ModelAdmin):

    list_display = ('name',)

    search_fields = ['name']


@admin.register(Tools)
class ToolsAdmin(admin.ModelAdmin):
    pass


@admin.register(DiceEvent)
class DiceEventAdmin(admin.ModelAdmin):
    pass
