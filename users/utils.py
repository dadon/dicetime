from users.models import Texts


def get_localized_choice(user, pk=None, ru_text='', en_text=''):
    if user.language.pk == 1:
        text = Texts.objects.get(pk=pk).text_ru if pk else ru_text
    else:
        text = Texts.objects.get(pk=pk).text_eng if pk else en_text
    return text
