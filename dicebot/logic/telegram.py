import logging
from datetime import datetime

from pyrogram import Client, Chat
from pyrogram.api.functions.channels import GetFullChannel
from pyrogram.api.functions.messages import GetFullChat
from pyrogram.api.types import InputPeerChat, InputPeerChannel, Channel as TChannel, Chat as TChat
from pyrogram.client.methods.chats.iter_chat_members import Filters
from pyrogram.errors import ChannelInvalid, ChannelPrivate

logger = logging.getLogger('Dice')


def collect_chat_members(app: Client, chat):
    try:
        return [m for m in app.iter_chat_members(chat.chat_id)]
    except (AttributeError, ChannelInvalid, ChannelPrivate) as exc:
        logger.info(f'Error for {chat.title_chat} ({chat.chat_id})')
        logger.info(exc)
        return []


def get_chatmember_joined_date(app: Client, user, chat):
    if user.id == chat.creator.id:
        return chat.created_at

    members = collect_chat_members(app, chat)
    for m in members:
        if m.user.id == user.id:
            return datetime.utcfromtimestamp(m.joined_date) if m.joined_date else None


def get_chat_creator(chat: Chat):
    logger.info(f'====[get_chat_creator]==== iter chat admins {chat}')
    for member in chat.iter_members(filter=Filters.ADMINISTRATORS):
        logger.info(member)
        logger.info('\n')
        if member.status != 'creator':
            continue
        logger.info('####[get_chat_creator]####')
        return member.user
    logger.info('####[get_chat_creator]####')


def get_fullchat(app, chat_id):
    peer = app.resolve_peer(chat_id)
    if isinstance(peer, InputPeerChannel):
        return app.send(GetFullChannel(channel=peer))
    if isinstance(peer, InputPeerChat):
        return app.send(GetFullChat(chat_id=peer.chat_id))


def _chat_date(app, chat: TChannel, source_chat_id):
    chat_date = chat.date
    if isinstance(chat, TChannel) and not chat.megagroup:
        chat_date = chat.date
        logger.info(f'####### [GetFullChat] - Got chat ({chat.id} {chat.title}) date: {chat_date}')
    else:
        messages = filter(
            lambda m: not m.empty,
            app.get_messages(source_chat_id, range(1, 201), replies=0))
        for msg in messages:
            chat_date = msg.date
            logger.info(f'####### [GetFullChat + get_messages] - Got chat ({chat.id} {chat.title}) date: {chat_date}')
            break
    return chat_date


def get_chat_creation_date(app: Client, chat_id):
    chat_date = None
    full = get_fullchat(app, chat_id)
    if len(full.chats) == 1:
        chat = full.chats[0]
        chat_date = _chat_date(app, chat, chat_id)
    else:
        for chat in full.chats:
            if chat.broadcast:
                continue
            chat_date = _chat_date(app, chat, chat_id)
            break

    if chat_date is None:
        raise Exception(f"Can't get chat date\n{str(full)}")

    return datetime.utcfromtimestamp(chat_date)
