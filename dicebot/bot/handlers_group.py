import logging
import re
from datetime import datetime

from pyrogram import Client, Filters, Message

from dice_time.settings import RELEASE_UTC_DATETIME
from dicebot.bot.markup import markup_add_to_chat
from dicebot.logic.core import on_dice_event, send_coins
from dicebot.logic.domain import get_chat_model, get_user_model, get_chatmember_model
from dicebot.logic.helpers import normalize_text
from dicebot.logic.stats import is_user_won, get_user_won
from users.models import Triggers, Tools

logger = logging.getLogger('Dice')
logger_dice_event = logging.getLogger('DiceEvent')


@Client.on_message(Filters.text & Filters.group & ~Filters.forwarded, group=777)
def dice_time(client: Client, message: Message):
    msg_normalized = normalize_text(message.text)
    logging.info(f'New msg:\n{message}')
    for trigger in Triggers.objects.filter(action='dice'):
        if trigger.phrase.lower() not in msg_normalized:
            continue

        chat_obj, is_created = get_chat_model(client, message.chat)
        if chat_obj.status != 'activated':
            return

        now = datetime.utcnow()
        timenow = now.time()
        if timenow < chat_obj.dice_time_from or timenow > chat_obj.dice_time_to:
            return

        # проверяем  положен ли выигрыш
        today = now.date()

        user, is_created = get_user_model(message.from_user)
        chatmember, _ = get_chatmember_model(client, user, chat_obj)
        release_datetime = datetime.strptime(RELEASE_UTC_DATETIME, '%Y-%m-%d %H:%M')
        if chatmember.joined_date > release_datetime:
            logger.info(f'### Restrict chat member {chatmember} by joined_date')
            return

        user_won_this_chat_today = is_user_won(user, message.chat.id, today) \
            if not is_created else False

        user.init_today_state(today)

        warned_here = user.today_state['warned_chats'].setdefault(str(message.chat.id), 0)
        if user_won_this_chat_today:
            if warned_here >= 1:
                user.save()
                return

            button_text = 'Попробовать в другом чате'
            reply_text = 'В этом чате вы уже не можете сегодня играть.' \
                '\nНе нужно спамить чат, мой уважаемый друг'
            bot = client.get_me()
            message.reply(reply_text, reply_markup=markup_add_to_chat(bot.username, button_text))
            user.today_state['warned_chats'][str(message.chat.id)] += 1
            user.save()
            return

        settings = Tools.objects.get(pk=1)
        user_today_won = get_user_won(user, today)
        warned_today = user.today_state['warned_today']
        if user_today_won >= settings.user_limit_day:
            if warned_today >= 1:
                user.save()
                return

            reply_text = 'Сегодня вы не можете больше играть.' \
                '\nНе нужно спамить чат, мой уважаемый друг'
            message.reply(reply_text)
            user.today_state['warned_today'] += 1
            user.save()
            return

        user.save()

        logger.info('######## Dice Event')
        logger_dice_event.info(f'\nDice event: {user} in chat#{message.chat.id} "{message.chat.title}"')
        on_dice_event(client, message, user, chat_obj)
        return


@Client.on_message(Filters.text & Filters.group & Filters.reply, group=0)
def calc_reputation(_, message: Message):
    msg_normalized = normalize_text(message.text)
    original_msg = message.reply_to_message
    sender_user = message.from_user
    receiver_user = original_msg.from_user
    if sender_user.id == receiver_user.id:
        return
    user, _ = get_user_model(receiver_user)

    user.reply_count += 1
    user.save()

    if len(message.text) > 20:
        return

    downvote_triggers = Triggers.objects.filter(action='downvote')
    is_downvote = any(
        t.phrase == msg_normalized if t.exact else t.phrase.lower() in msg_normalized
        for t in downvote_triggers)
    if is_downvote:
        user.downvotes += 1
        user.save()
        return

    upvote_triggers = Triggers.objects.filter(action='upvote')
    is_upvote = any(
        t.phrase == msg_normalized if t.exact else t.phrase.lower() in msg_normalized
        for t in upvote_triggers)
    if is_upvote:
        user.upvotes += 1
        user.save()
        return


@Client.on_message(Filters.group & Filters.reply & Filters.regex('^\s*send.*', flags=re.IGNORECASE), group=1)
def send_coins_reply(client: Client, message: Message):
    original_msg = message.reply_to_message
    sender_user = message.from_user
    receiver_user = original_msg.from_user
    receiver, _ = get_user_model(receiver_user)

    # 777000=Telegram. This is channel post
    if receiver_user.id == 777000:
        chat_obj, _ = get_chat_model(client, message.chat)
        receiver = chat_obj.creator
    if receiver.id == sender_user.id:
        return
    sender, _ = get_user_model(sender_user)
    send_coins(message, sender, receiver)
