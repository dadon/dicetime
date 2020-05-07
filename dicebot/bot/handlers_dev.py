from datetime import date

from pyrogram import Client, Filters, Message

from dice_time.settings import ADMIN_TG_IDS
from dicebot.logic.dev import send_test_dice
from dicebot.logic.domain import get_user_model, get_chat_model
from users.models import DiceEvent


@Client.on_message(Filters.command('dice') & (Filters.private | (Filters.group & Filters.create(lambda _, m: m.from_user.id in ADMIN_TG_IDS))), group=999)
def dice_test(client: Client, message: Message):
    tg_user = message.from_user
    if message.reply_to_message:
        tg_user = message.reply_to_message.from_user

    user, _ = get_user_model(tg_user)
    send_test_dice(client, user, message)


@Client.on_message(Filters.command('del') & Filters.create(lambda _, m: m.from_user.id in ADMIN_TG_IDS), group=999)
def dice_del(client: Client, message: Message):
    tg_user = message.from_user
    if message.reply_to_message:
        tg_user = message.reply_to_message.from_user

    user, _ = get_user_model(tg_user)
    today = date.today()
    DiceEvent.objects.filter(user=user, date__date=today, is_win=True).update(is_win=False)
    message.delete()


@Client.on_message(Filters.group & Filters.command(['restrict', 'allow']) & Filters.create(lambda _, m: m.from_user.id in ADMIN_TG_IDS), group=999)
def dice_chat_toogle(client: Client, message: Message):
    chat, _ = get_chat_model(client, message.chat)
    new_status = {
        'restrict': 'restricted',
        'allow': 'activated'
    }[message.command[0]]

    chat.status = new_status
    chat.save()
    client.send_message(message.from_user.id, f'Updated **{message.chat.title}** status to `{new_status}`')
    message.delete()
