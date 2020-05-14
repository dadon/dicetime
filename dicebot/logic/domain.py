import logging
from datetime import datetime
from typing import Union

from pyrogram import Client, Chat, User as tgUser
from mintersdk.sdk.wallet import MinterWallet

from dice_time.settings import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, RELEASE_UTC_DATETIME
from dicebot.logic.telegram import get_chatmember_joined_date, get_chat_creator, get_chat_creation_date
from users.models import ChatMember, AllowedChat, Language, User, MinterWallets, Payment

logger = logging.getLogger('Dice')


def get_chatmember_model(app: Client, user, chat):
    chatmember, is_created = ChatMember.objects.get_or_create(
        chat=chat,
        user=user
    )

    chatmember.joined_date = get_chatmember_joined_date(app, user, chat)
    if chatmember.joined_date is None:
        logger.warning('### Cant get user joined date. Setting "now"')
        chatmember.joined_date = datetime.utcnow()

    chatmember.save()
    return chatmember, is_created


def get_chat_model(app: Client, tg_chat: Chat, recalc_creation_date=True):
    chat_obj, is_created = AllowedChat.objects.get_or_create(
        chat_id=tg_chat.id,
        defaults={
            'link_chat': tg_chat.username,
            'title_chat': tg_chat.title
        })

    if not chat_obj.creator:
        tg_creator = get_chat_creator(tg_chat)
        creator_user, _ = get_user_model(tg_creator)
        chat_obj.creator = creator_user
        chat_obj.save()

    if recalc_creation_date and chat_obj.status in [None, 'errored']:
        chat_date = None
        try:
            chat_date = get_chat_creation_date(app, tg_chat.id)
            chat_obj.created_at = chat_date
        except Exception as exc:
            logger.error(
                f'\nGet chat creation date error. '
                f'id={tg_chat.id} type={tg_chat.type} title={tg_chat.title}\n\n'
                f'{type(exc)}: {exc}\n')

        release_datetime = datetime.strptime(RELEASE_UTC_DATETIME, '%Y-%m-%d %H:%M')
        chat_obj.status_updated_at = datetime.utcnow()
        chat_obj.status = 'errored' if not chat_date \
            else 'restricted' if chat_date > release_datetime \
            else 'activated'
        chat_obj.save()
    return chat_obj, is_created


def get_user_model(tg_user: tgUser):
    lang_pk = {'ru': 1, 'en': 2}
    user_lang = (tg_user.language_code or DEFAULT_LANGUAGE).split("-")[0]
    user_lang = DEFAULT_LANGUAGE if user_lang not in SUPPORTED_LANGUAGES else user_lang
    user_lang_model = Language.objects.get(pk=lang_pk[user_lang])

    user, is_created = User.objects.get_or_create(
        id=tg_user.id, defaults={
            'last_name': tg_user.last_name,
            'first_name': tg_user.first_name,
            'username': tg_user.username,
            'language': user_lang_model
        })

    wallet = MinterWallet.create()
    MinterWallets.objects.get_or_create(
        user=user, defaults={
            'address': wallet['address'],
            'mnemonic': wallet['mnemonic']
        })

    # try change lang when user changes lang
    if not is_created and user.language != user_lang_model:
        user.language = user_lang_model
        user.save()
    return user, is_created


def schedule_payment(event, wallet_local=None):
    if not event.summa:
        return
    event.is_payed = True
    event.save()
    wallet_to = MinterWallets.objects.get(user=event.user).address
    Payment.objects.create(
        user=event.user,
        event=event,
        to=wallet_to,
        coin=event.coin,
        amount=event.summa,
        wallet_local=wallet_local)


def is_user_input_expected(user: Union[tgUser, User]):
    if isinstance(user, tgUser):
        user, _ = get_user_model(user)
    return 'await_input_type' in user.conversation_flags
