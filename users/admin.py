from django.contrib import admin
from django import forms
from dal import autocomplete

from .models import *


class ExceptionsForm(forms.ModelForm):
    user = forms.ModelChoiceField(
            queryset=User.objects.all(),
            widget=autocomplete.ModelSelect2(url='username_select2')
            )

    class Meta:
        model = Exceptions
        fields = ('__all__')


@admin.register(Exceptions)
class ExceptionsAdmin(admin.ModelAdmin):
    form = ExceptionsForm
    list_display = ('user',)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    
    list_display = ('id', 'first_name', 'last_name', 'username')

    search_fields = ['id', 'first_name', 'last_name', 'username']


@admin.register(MinterWallets)
class WalletAdmin(admin.ModelAdmin):

    list_display = ('user', 'address', 'balance', 'balance_updated_at')

    search_fields = ['user', 'address', 'balance', 'balance_updated_at']


@admin.register(Tools)
class ToolsAdmin(admin.ModelAdmin):
    list_display = ('address', 'payload', 'coin', 'user_limit_day', 'chat_limit_day', 'total_limit_day')


@admin.register(DiceEvent)
class DiceEventAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'date', 'summa', 'is_win', 'is_payed',
        'chat_id', 'title_chat', 'link_chat',
    )

    search_fields = ['user', 'title_chat', 'chat_id']


@admin.register(Texts)
class TextsAdmin(admin.ModelAdmin):
    list_display_links = None
    list_display = ('name', 'text_ru', 'text_eng')
    list_editable = ['name', 'text_ru', 'text_eng']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Triggers)
class TriggersAdmin(admin.ModelAdmin):
    list_display_links = None
    list_display = 'phrase', 'action', 'exact'
    list_editable = 'phrase', 'action', 'exact'
