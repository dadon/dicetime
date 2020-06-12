import logging
from time import sleep

from django.core.management.base import BaseCommand
from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError, ChannelInvalid, ChannelPrivate, PeerIdInvalid

from dice_time.settings import TG_API_ID, TG_API_HASH, API_TOKEN

logger = logging.getLogger('Dice')


FS_PROMO_TEXT = '''
Привет, у меня хорошие новости! 

Добавилась новая команда - **fs**

Если ее написать в чате, в котором есть я, то появится специальная ссылка на секретную виртуальную комнату этого чата. В ней можно общаться с помощью видео связи прямо в браузере, без установки каких-либо дополнительных программ. 

Комната создана в Friendoscope, отсюда и название команды - **fs** (**F**riendo**S**cope)

В этой комнате может общаться сразу несколько человек. Можно заходить и выходить в любой момент.  
Можно играть в игры, рисовать приличные рисунки и шарить экран. Выпивать и распевать. Изливать и обучать. Скидывать смешные гифки и серьезные картинки. Смотреть вместе youtube ролики, наконец.  

Ну и, конечно, просто болтать с друзьями
'''


def collect_chat_members(app: Client, chat_id, chat_title=None):
    try:
        return [m for m in app.iter_chat_members(chat_id)]
    except (AttributeError, ChannelInvalid, ChannelPrivate, PeerIdInvalid) as exc:
        logger.info(f'Error for chat {chat_title} ({chat_id})')
        logger.info(exc)
        return []


def broadcast_users(app, user_ids, text):
    logger.info(f'Broadcast for {len(user_ids)} started.')
    count_success = 0
    count_error = 0
    for uid in user_ids:
        try:
            app.send_message(uid, text)
            count_success += 1
        except FloodWait as exc:
            sleep(exc.x)
            app.send_message(uid, text)
            count_success += 1
        except RPCError as exc:
            logger.info(f'############### error for user {uid}')
            logger.info(f'\n\n{type(exc)}: {exc}\n\n')
            count_error += 1
    logger.info(f'Broadcast done. count_success={count_success} count_error={count_error}')


def broadcast_chat_members(app, chat_ids, text):
    uids = set()
    for chat_id in chat_ids:
        members = collect_chat_members(app, chat_id=chat_id)
        uids.update(member.user.id for member in members)
        logger.info(f'Got {len(members)} members from chat {chat_id}. Potential recipients {len(uids)}')
    broadcast_users(app, uids, text)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--chatlist')

    def handle(self, **options):
        chat_list = options.get('chatlist')
        chat_ids = []
        if not chat_list:
            return
        with open(chat_list, 'r') as f:
            for line in f:
                chat_ids.append(int(line))

        if not chat_ids:
            logger.info('Chatlist empty :(')
        logger.info(f'Got {len(chat_ids)} chats')

        with Client('pyrosession', api_id=TG_API_ID, api_hash=TG_API_HASH, bot_token=API_TOKEN) as app:
            broadcast_chat_members(app, chat_ids, FS_PROMO_TEXT)
