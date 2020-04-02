from telebot import types
from .models import Language

language_markup =  types.InlineKeyboardMarkup(row_width=1)
for lang in Language.objects.all():
    language_markup.add(types.InlineKeyboardButton(str(lang.name),
                callback_data='languag.id.{}'.format(lang.id)))


HOME_MARKUP = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
HOME_MARKUP.add(
    types.KeyboardButton('⚠️ Правила'),
    types.KeyboardButton('💰 Мой Кошелёк')
)

#take_money_markup = types.InlineKeyboardMarkup(row_width=1)
# take_money_markup.add(types.InlineKeyboardButton(str(event.name),
#                callback_data='event.id.{}'.format(event.id)))
