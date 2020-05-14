from random import randint

from pyrogram import Message, Client

from dicebot.bot.markup import KB_REMOVE, kb_home
from dicebot.logic.core import calc_dice_reward
from users.models import User


def send_test_dice(app: Client, user: User, message: Message):
    args = message.command[1:]
    dice, chat_id = None, message.chat.id

    if len(args) == 1 and args[0].isdigit():
        dice = int(args[0])
    if not dice:
        dice = randint(1, 6)

    reward, details = calc_dice_reward(app, user, None, dice, chat_id)

    details_pretty = '\n'.join([f'    {param}: {str(value)}' for param, value in sorted(details.items())])
    response = f"""
Dice testdata for [{user.username or user.first_name}](tg://user?id={user.id})
```Dice: {dice}
Reward: {reward}
Details:

{details_pretty}```"""
    markup = KB_REMOVE if message.chat.type != 'private' else kb_home(user)
    message.reply(response, quote=False, reply_markup=markup)
