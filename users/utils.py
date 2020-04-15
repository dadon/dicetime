from dice_time.settings import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
from users.models import Text


def get_localized_choice(user, pk=None, ru_text='', en_text=''):
    if user.language.pk == 1:
        text = Text.objects.get(pk=pk).text_ru if pk else ru_text
    else:
        text = Text.objects.get(pk=pk).text_eng if pk else en_text
    return text


def get_language(lang_code):
    lang_code = lang_code or 'en'
    lang_code = lang_code.split("-")[0]
    if lang_code in SUPPORTED_LANGUAGES:
        return lang_code
    return DEFAULT_LANGUAGE
