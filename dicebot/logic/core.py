import logging
from datetime import datetime
from pprint import pformat
from typing import Union

from mintersdk.sdk.wallet import MinterWallet
from pyrogram import Client, Message, CallbackQuery
from pyrogram.errors import ChannelInvalid

from dicebot.bot.markup import markup_take_money, markup_chat_actions, markup_add_to_chat, markup_chat_list
from dicebot.logic.domain import schedule_payment
from dicebot.logic.helpers import truncate
from dicebot.logic.minter import coin_convert
from dicebot.logic.stats import get_user_won_by_chats, get_chat_won, get_total_won_by_chats
from dicebot.logic.tasks import minter_send_coins
from users.models import User, AllowedChat, ChatWallet, DiceEvent, Exceptions, Tools, MinterWallets, ChatMember

logger = logging.getLogger('Dice')
logger_dice_event = logging.getLogger('DiceEvent')


def on_dice_event(app: Client, message: Message, user: User, chat: AllowedChat, chatmember: ChatMember):
    dice_msg = app.send_dice(
        message.chat.id,
        disable_notification=True,
        reply_to_message_id=message.message_id)

    reward, details = calc_dice_reward(app, user, chatmember, dice_msg.dice.value, message.chat.id)

    is_win = bool(reward)
    event = DiceEvent.objects.create(
        user=user,
        chat_id=message.chat.id,
        title_chat=message.chat.title,
        link_chat=message.chat.username,
        summa=reward,
        is_win=is_win,
        is_local=False)

    if not is_win:
        return

    wallet_local = ChatWallet.objects.filter(chat=chat).first()
    event_local = None
    reward_local = None
    if wallet_local and wallet_local.balance[chat.coin] > 0:
        reward_local = calc_dice_reward_local(user, chat, details)
        event_local = DiceEvent.objects.create(
            user=user,
            chat_id=message.chat.id,
            title_chat=message.chat.title,
            link_chat=message.chat.username,
            summa=reward_local,
            is_win=is_win,
            is_local=True,
            coin=chat.coin)

    logger_dice_event.info(f'Reward: {reward}')
    logger_dice_event.info(f'Reward (local): {reward_local}')
    logger_dice_event.info(f'Details:\n\n{pformat(details)}\n\n')

    schedule_payment(event)
    if event_local:
        schedule_payment(event_local, wallet_local=wallet_local)

    _notify_win(app, user, event, event_local=event_local)
    _button_win(app, user, dice_msg, event, event_local=event_local)


def wilson_score(up, down, z=1.64485):
    """
    https://habr.com/ru/company/darudar/blog/143188/
    отрицательное значение при up=0
    """
    if not up:
        return - min(100, down) / 100
    if not up and not down:
        return 0

    total = up + down
    up_rate = up / total
    return (
       up_rate + z ** 2 / (2 * total) -
       z * ((up_rate * (1 - up_rate) + z ** 2 / (4 * total)) / total) ** 0.5) / (1 + z ** 2 / total)


def calc_dice_reward_local(user, chat_local, details):
    if details['blacklisted'] or details['is_chat_win']:
        return 0

    details['user_limit_day_local'] = user_limit_day = float(chat_local.user_limit_day)
    details['chat_limit_day_local'] = chat_limit_day = float(chat_local.chat_limit_day)

    if user_limit_day > 0:
        user_agg = get_user_won_by_chats(user, details['today'], is_local=True, coin=chat_local.coin)
        user_won_day = float(sum(row['chat_sum_user'] for row in user_agg)) if user_agg else 0
        details['user_won_day_local'] = user_won_day
        user_limit_multiplier = max(1 - user_won_day / user_limit_day, 0)
    else:
        user_limit_multiplier = 1

    if chat_limit_day > 0:
        chat_won_day = float(get_chat_won(
            chat_local.chat_id, details['today'], is_local=True, coin=chat_local.coin))
        details['chat_won_local'] = chat_won_day
        chat_limit_multiplier = max(1 - chat_won_day / chat_limit_day, 0)
    else:
        chat_limit_multiplier = 1

    details['user_limit_multiplier'] = user_limit_multiplier
    details['chat_limit_multiplier'] = chat_limit_multiplier
    details['dice_multiplier_local'] = dice_multiplier = details['dice_multiplier'] / 5

    if user_limit_multiplier < 0 or chat_limit_multiplier < 0:
        return 0

    reward = user_limit_day * details['user_reputation'] * \
        dice_multiplier * user_limit_multiplier * chat_limit_multiplier

    if reward <= 0:
        return 0

    reward_bip = coin_convert(chat_local.coin, reward, 'BIP')
    if 0 < reward_bip < 0.05:
        reward_bip = 0.05
        reward = coin_convert('BIP', reward_bip, chat_local.coin)
    return truncate(max(0, reward), 4)


def calc_dice_reward(app: Client, user, chatmember, dice, chat_id):
    details = {}
    is_blacklisted = Exceptions.objects.filter(user=user).exists()
    details['blacklisted'] = is_blacklisted
    if is_blacklisted:
        return 0, details
    now = datetime.utcnow()
    details['today'] = today = now.date()
    try:
        details['members'] = members = app.get_chat_members_count(chat_id)
    except ValueError:
        details['members'] = members = 2
    user_agg = get_user_won_by_chats(user, today, is_local=False)
    user_won_day = float(sum(row['chat_sum_user'] for row in user_agg)) if user_agg else 0
    is_chat_win = chat_id in [row['chat_id'] for row in user_agg]
    details['user_won_day'] = user_won_day
    details['is_chat_win'] = is_chat_win

    chat_stat = get_total_won_by_chats(today, is_local=False)
    details['chat_won_day'] = chat_won_day = float(chat_stat.get(chat_id, 0))
    details['total_won_day'] = total_won_day = float(sum(chat_stat.values()))

    user_settings = Tools.objects.get(pk=1)
    details['user_limit_day'] = user_limit_day = float(user_settings.user_limit_day)
    details['chat_limit_day'] = chat_limit_day = float(user_settings.chat_limit_day)
    details['total_limit_day'] = total_limit_day = float(user_settings.total_limit_day)

    chat_size_multiplier = members / user_settings.members_limit
    details['chat_size_multiplier'] = 1 if chat_size_multiplier > 1 else chat_size_multiplier
    details['user_limit_multiplier'] = user_limit_multiplier = 1 - user_won_day / user_limit_day
    details['chat_limit_multiplier'] = chat_limit_multiplier = 1 - chat_won_day / chat_limit_day
    details['total_limit_multiplier'] = total_limit_multiplier = 1 - total_won_day / total_limit_day

    dice_multiplier = dice - 1
    if dice_multiplier < 0:
        dice_multiplier = 0
    if dice_multiplier > 5:
        dice_multiplier = 5
    details['dice'] = dice
    details['dice_multiplier'] = dice_multiplier

    if chatmember:
        user_reputation = wilson_score(chatmember.upvotes, chatmember.downvotes)
        details['user_upvotes'] = chatmember.upvotes
        details['user_downvotes'] = chatmember.downvotes
        details['user_reply_count'] = chatmember.reply_count
        details['user_reputation'] = user_reputation
        details['user_lifetime'] = (now - chatmember.joined_date).total_seconds()

    if is_chat_win:
        return 0, details

    if chat_size_multiplier < 0 or user_limit_multiplier < 0 or chat_limit_multiplier < 0 or total_limit_multiplier < 0:
        return 0, details

    reward = dice_multiplier * chat_size_multiplier * \
             user_limit_multiplier * chat_limit_multiplier * \
             total_limit_multiplier * (user_reputation + 1)

    if reward + user_won_day > user_limit_day:
        reward = user_limit_day - user_won_day

    reward_bip = coin_convert(user_settings.coin, reward, 'BIP')
    if 0 < reward_bip < 0.05:
        reward_bip = 0.05
        reward = coin_convert('BIP', reward_bip, user_settings.coin)
    return truncate(max(0, reward), 4), details


def _notify_win(app: Client, user: User, event, event_local=None):
    local_text = ''
    if event_local:
        local_text = f' + {event_local.summa} {event_local.coin}'
    win_text = user.choice_localized(text_name='msg-chat-win-notify')
    win_text = win_text.format(X=event.summa, coin=event.coin) + local_text
    app.send_message(user.id, win_text)

    event.is_notified = True
    event.save()


def _button_win(app: Client, user: User, dice_msg: Message, event, event_local=None):
    take_money_btn_text = user.choice_localized(text_name='btn-chat-win')
    take_money_msg_text = user.choice_localized(text_name='msg-chat-win').format(X=event.summa, coin_ticker=event.coin)
    if event_local:
        take_money_msg_text += f' + {event_local.summa} {event_local.coin}'
    bot = app.get_me()
    dice_msg.reply(take_money_msg_text, reply_markup=markup_take_money(bot.username, take_money_btn_text))


def send_coins(message, sender, receiver):
    msg_parts = list(filter(None, str(message.text).lower().split(' ')))
    if len(msg_parts) < 2:
        return
    if msg_parts[0] != 'send':
        return
    try:
        amount = float(msg_parts[1])
    except Exception:
        return

    coin = 'TIME' if len(msg_parts) == 2 else msg_parts[2].upper()

    w_from = MinterWallets.objects.get(user=sender)
    w_to = MinterWallets.objects.get(user=receiver)
    mw_from = MinterWallet.create(w_from.mnemonic)
    minter_send_coins.delay(
        mw_from, w_to.address, coin, amount,
        message.chat.id, sender.id, receiver.id, sender.profile_markdown, receiver.profile_markdown)


#  ===============


def handle_missed_notifications(app: Client, user: User):
    missed_notifies = DiceEvent.objects.filter(user=user, is_win=True, is_notified=False)
    count = len(missed_notifies)
    if not count:
        return
    missed_notifies.update(is_notified=True)

    notify_text = user.choice_localized(text_name='msg-notify-missed-rewards')
    app.send_message(user.id, notify_text, reply_markup=user.home_markup)


def send_chat_detail(client: Client, chat: AllowedChat, user, root_message_id):
    chat.refresh_from_db()
    w = MinterWallet.create()
    chat_wallet, _ = ChatWallet.objects.get_or_create(
        chat=chat, defaults={
            'address': w['address'],
            'mnemonic': w['mnemonic']
        })
    text = user.choice_localized(text_name='msg-owner-chat').format(
        address=chat_wallet.address, mnemonic=chat_wallet.mnemonic,
        coin=chat.coin, balances=chat_wallet.balance_formatted)
    btn_texts = {
        'ulimit': user.choice_localized(text_name='btn-chat-setting-ulimit'),
        'climit': user.choice_localized(text_name='btn-chat-setting-climit'),
        'dt': user.choice_localized(text_name='btn-chat-setting-dt'),
        'back': user.choice_localized(text_name='btn-chat-setting-back')
    }
    client.edit_message_text(user.id, root_message_id, text, reply_markup=markup_chat_actions(chat, btn_texts))


def send_chat_list(client: Client, user: User, update: Union[Message, CallbackQuery]):
    chats = AllowedChat.objects.filter(creator=user, status='activated')
    clean_chats = []
    for chat in chats:
        try:
            client.resolve_peer(chat.chat_id)
            clean_chats.append(chat)
        except ChannelInvalid as exc:
            logger.info(f'### Error {chat}: {type(exc)}: {exc}')

    if not clean_chats:
        text = user.choice_localized(text_name='msg-owner-empty')
        button_text = user.choice_localized(text_name='btn-owner-add-bot')
        bot = client.get_me()
        client.send_message(user.id, text, reply_markup=markup_add_to_chat(bot.username, button_text))
        return

    text = user.choice_localized(text_name='msg-owner')
    if isinstance(update, Message):
        update.reply_text(text, reply_markup=markup_chat_list(clean_chats))
    if isinstance(update, CallbackQuery):
        update.message.edit_text(text, reply_markup=markup_chat_list(clean_chats))
