import logging
from datetime import datetime
from decimal import Decimal

from mintersdk.sdk.check import MinterCheck
from mintersdk.sdk.deeplink import MinterDeeplink
from mintersdk.sdk.transactions import MinterRedeemCheckTx, MinterSendCoinTx
from mintersdk.sdk.wallet import MinterWallet
from pyrogram import Client, Filters, Message, CallbackQuery
from shortuuid import uuid

from dice_time.settings import ADMIN_TG_IDS
from dicebot.bot.markup import RULES_BTN_RU, RULES_BTN_EN, CHAT_ADMIN_RU, CHAT_ADMIN_EN, \
    WALLET_BTN_RU, WALLET_BTN_EN, markup_wallet, markup_add_to_chat, markup_chat_list
from dicebot.logic.core import handle_missed_notifications, send_chat_detail, send_chat_list
from dicebot.logic.domain import get_user_model, is_user_input_expected
from dicebot.logic.minter import API, coin_send
from dicebot.logic.timeloop import get_user_timeloop_address
from users.models import Tools, AllowedChat, MinterWallets

logger = logging.getLogger('DicePrivate')


@Client.on_message(Filters.private & Filters.command('start'))
def start(client: Client, message: Message):
    coin = Tools.objects.get(pk=1).coin
    user, is_created = get_user_model(message.from_user)
    handle_missed_notifications(client, user)
    if is_created:
        text = user.choice_localized(text_name='caption-tl-promo')
        document = 'content/ad1.mp4'
        client.send_document(user.id, document, caption=text, reply_markup=user.home_markup)
    else:
        text = user.choice_localized(text_name='msg-rules').format(
            user_name=user.first_name,
            coin_ticker=coin)
        client.send_message(user.id, text, reply_markup=user.home_markup)
    if user.id in ADMIN_TG_IDS:
        client.restart(block=False)


@Client.on_message(Filters.private & (Filters.regex(f'^{RULES_BTN_RU}$') | Filters.regex(f'^{RULES_BTN_EN}$')))
def rules(client: Client, message: Message):
    coin = Tools.objects.get(pk=1).coin
    user, _ = get_user_model(message.from_user)
    text = user.choice_localized(text_name='msg-rules').format(
        user_name=user.first_name,
        coin_ticker=coin)
    client.send_message(user.id, text, reply_markup=user.home_markup)


@Client.on_message(Filters.private & Filters.command([CHAT_ADMIN_RU, CHAT_ADMIN_EN], prefixes='', case_sensitive=True))
def chat_admin(client: Client, message: Message):
    user, _ = get_user_model(message.from_user)
    send_chat_list(client, user, message)


@Client.on_callback_query(Filters.create(lambda _, c: c.message.chat.type == 'private' and c.data.startswith('admin.')))
def chat_detail(client: Client, call: CallbackQuery):
    user, _ = get_user_model(call.from_user)
    chat_id = int(call.data.split('.')[-1])
    try:
        chat = AllowedChat.objects.get(chat_id=chat_id, creator=user, status='activated')
    except AllowedChat.DoesNotExist:
        return

    send_chat_detail(client, chat, user, call.message.message_id)


@Client.on_callback_query(Filters.create(lambda _, c: c.message.chat.type == 'private' and c.data.startswith('set.')))
def chat_setting(client: Client, call: CallbackQuery):
    user, _ = get_user_model(call.from_user)
    if call.data == 'set.back':
        send_chat_list(client, user, call)
        return

    if is_user_input_expected(user):
        return

    setting, chat_id = call.data.split('.')[1:]
    try:
        chat = AllowedChat.objects.get(chat_id=chat_id, creator=user, status='activated')
    except AllowedChat.DoesNotExist:
        return

    prompt_txt = user.choice_localized(text_name=f'msg-chat-setting-{setting}')
    if setting == 'dt':
        now = datetime.utcnow()
        prompt_txt = prompt_txt.format(now=now.strftime("%H:%M"))
    call.edit_message_text(prompt_txt)
    user.conversation_flags['await_input_type'] = setting
    user.conversation_flags['input_params'] = {
        'chat_id': str(chat_id),
        'root_message_id': str(call.message.message_id)
    }
    user.save()


@Client.on_message(Filters.private & Filters.create(lambda _, m: is_user_input_expected(m.from_user)))
def set_chat_param(client: Client, message: Message):
    user, _ = get_user_model(message.from_user)
    message.delete()
    setting = user.conversation_flags['await_input_type']
    chat_id = int(user.conversation_flags['input_params']['chat_id'])
    root_message_id = int(user.conversation_flags['input_params']['root_message_id'])
    user.conversation_flags = {}
    user.save()
    try:
        chat = AllowedChat.objects.get(chat_id=chat_id, creator=user, status='activated')
    except AllowedChat.DoesNotExist:
        return

    try:
        if setting == 'dt':
            f, t = message.text.split('-')
            if f > t:
                raise ValueError(f'From > To: ({f} - {t})')
            chat.dice_time_from = f
            chat.dice_time_to = t
            chat.save()
        elif setting in ['ulimit', 'climit']:
            text_parts = message.text.split()
            limit = text_parts[0]
            chat.coin = 'TIME' if len(text_parts) == 1 else text_parts[1].upper()
            if setting == 'ulimit':
                chat.user_limit_day = Decimal(limit)
            if setting == 'climit':
                chat.chat_limit_day = Decimal(limit)
            chat.save()

    except Exception as exc:
        logger.debug(f'### {type(exc)}: {exc}')

    send_chat_detail(client, chat, user, root_message_id)


@Client.on_message(Filters.private & (Filters.regex(f'^{WALLET_BTN_RU}$') | Filters.regex(f'^{WALLET_BTN_EN}$')))
def my_wallet(client: Client, message: Message):
    user, _ = get_user_model(message.from_user)
    wallet = MinterWallets.objects.get(user=user)
    wallet_obj = MinterWallet.create(mnemonic=wallet.mnemonic)
    private_key = wallet_obj['private_key']

    coin = Tools.objects.get(pk=1).coin
    amount = wallet.balance[coin]
    nonce = API.get_nonce(wallet.address)

    check_obj = MinterCheck(
        nonce=1, due_block=999999999, coin=coin, value=amount, gas_coin=coin, passphrase=wallet.mnemonic)
    check_str = check_obj.sign(private_key)
    redeem_tx = MinterRedeemCheckTx(check_str, check_obj.proof(wallet.address, ''), nonce=1, gas_coin=coin)
    redeem_tx.sign(private_key)
    redeem_tx_fee = API.estimate_tx_commission(redeem_tx.signed_tx, pip2bip=True)['result']['commission']
    logger.info(f'Wallet {wallet.address} balance (check): {wallet.balance}')
    logger.info(f'Redeem check tx fee: {redeem_tx_fee}')
    available_withdraw = amount - redeem_tx_fee

    send_tx = MinterSendCoinTx(coin, wallet.address, amount, nonce=nonce, gas_coin=coin)
    send_tx.sign(wallet_obj['private_key'])
    send_tx_fee = API.estimate_tx_commission(send_tx.signed_tx, pip2bip=True)['result']['commission']
    logger.info(f'Send tx fee: {send_tx_fee}')
    available_send = amount - send_tx_fee

    to_wallet_text = None
    timeloop_text = None
    redeem_url = None
    user_address = None
    if available_withdraw > 0:
        to_wallet_text = user.choice_localized(text_name='btn-withdraw-minter')
        passphrase = uuid()
        check_obj = MinterCheck(
            nonce=1, due_block=999999999, coin=coin, value=available_withdraw, gas_coin=coin,
            passphrase=passphrase)
        check_str = check_obj.sign(private_key)
        redeem_tx = MinterRedeemCheckTx(check_str, proof='', nonce=nonce, gas_coin=coin)
        redeem_dl = MinterDeeplink(redeem_tx, data_only=True)
        redeem_dl.gas_coin = coin
        redeem_url = redeem_dl.generate(password=passphrase)
        logger.info(redeem_url)

    if available_send > 0:
        user_address = get_user_timeloop_address(message.chat.id)
        logger.info(f'User TL: {user_address}')
        timeloop_text = user.choice_localized(text_name='btn-withdraw-timeloop')

    markup = markup_wallet(
        to_wallet_text=to_wallet_text,
        redeem_deeplink=redeem_url,
        timeloop_text=timeloop_text,
        user_address=user_address)
    text = user.choice_localized(text_name='msg-wallet').format(
        user_wallet_address=wallet.address,
        user_seed_phrase=wallet.mnemonic,
        amount=wallet.balance_formatted)
    client.send_message(user.id, text, reply_markup=markup)


@Client.on_callback_query(Filters.create(lambda _, c: c.message.chat.type == 'private' and c.data.startswith('timeloop_')))
def timeloop(client: Client, call: CallbackQuery):
    user, _ = get_user_model(call.from_user)
    coin = 'TIME'
    wallet = MinterWallets.objects.get(user=user)
    wallet_obj = MinterWallet.create(mnemonic=wallet.mnemonic)
    amount = wallet.balance[coin]
    nonce = API.get_nonce(wallet.address)

    send_tx = MinterSendCoinTx(coin, wallet.address, amount, nonce=nonce, gas_coin=coin)
    send_tx.sign(wallet_obj['private_key'])
    tx_fee = API.estimate_tx_commission(send_tx.signed_tx, pip2bip=True)['result']['commission']
    available_send = amount - tx_fee

    user_timeloop_address = call.data.split('_')[-1]
    if not user_timeloop_address:
        alert_text = user.choice_localized(text_name='alert-tl-no-account')
        client.answer_callback_query(call.id, text=alert_text)
        return

    if available_send <= 0:
        alert_text = user.choice_localized(text_name='alert-tl-no-money')
        client.answer_callback_query(call.id, text=alert_text)
        return

    coin_send(
        wallet_obj['private_key'], wallet_obj['address'], user_timeloop_address, coin, available_send, gas_coin=coin)
    alert_text = user.choice_localized(text_name='alert-tl-success')
    client.answer_callback_query(call.id, text=alert_text)
