from telebot import types
from .models import Language

language_markup =  types.InlineKeyboardMarkup(row_width=1)
for lang in Language.objects.all():
    language_markup.add(types.InlineKeyboardButton(str(lang.name),
                callback_data='languag.id.{}'.format(lang.id)))


HOME_MARKUP_RU = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
HOME_MARKUP_RU.add(
    types.KeyboardButton('⚠️ Правила'),
    types.KeyboardButton('💰 Мой Кошелёк')
)

HOME_MARKUP_ENG = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
HOME_MARKUP_ENG.add(
    types.KeyboardButton('⚠️ Rooles'),
    types.KeyboardButton('💰 My wallet')
)
