from pyrogram import Client, Filters, ReplyKeyboardRemove

from dicebot.bot.markup import markup_tutorial, kb_home
from dicebot.logic.domain import get_user_model


@Client.on_callback_query(Filters.create(lambda _, cb: cb.data[:8] == 'tutorial'))
def tutorial_navigator(cli, cb):
    user, _ = get_user_model(cb.from_user)

    params = cb.data.split('-')
    action = params[2]
    tutorial_name = params[1]

    if action == 'end':

        if tutorial_name not in user.achievements['tutorials']:
            user.achievements['tutorials'].append(tutorial_name)

        user.save()

        cb.message.delete()
        return cb.message.reply(user.choice_localized(f'tutorial-{tutorial_name}-end'), reply_markup=kb_home(user))

    if action == 'continue':
        user.conversation_tutorial[tutorial_name]['step'] += 1

    if action == 'back':
        user.conversation_tutorial[tutorial_name]['step'] -= 1

    user.save()
    cb.message.edit(user.get_tutorial_text(tutorial_name), reply_markup=markup_tutorial(user, tutorial_name))


def start_turorial(cli, user, tutorial_name, step=None):
    if not step:
        step = 1

    if 'tutorials' not in user.achievements:
        user.achievements['tutorials'] = []

    if tutorial_name not in user.achievements['tutorials']:
        msg = cli.send_message(user.id, 'Загрузка туториала', reply_markup=ReplyKeyboardRemove())
        msg.delete()

    if tutorial_name in user.conversation_tutorial:
        user.conversation_tutorial[tutorial_name]['step'] = step
    else:
        user.conversation_tutorial[tutorial_name] = dict(step=1)

    user.save()
    txt = user.get_tutorial_text(tutorial_name, step)

    cli.send_message(user.id, txt, reply_markup=markup_tutorial(user, tutorial_name))


@Client.on_message(Filters.regex(r'p'))
def ewq(cli, m):
    user, _ = get_user_model(m.from_user)

    start_turorial(cli, user, 'name', step=None)