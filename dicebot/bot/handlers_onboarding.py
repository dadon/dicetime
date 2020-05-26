from pyrogram import Client, Filters

from dicebot.bot.markup import markup_tutorial
from dicebot.logic.domain import get_user_model


@Client.on_callback_query(Filters.create(lambda _, cb: cb.data[:8] == 'tutorial'))
def tutorial_navigator(cli, cb):
    user, _ = get_user_model(cb.from_user)

    params = cb.data.split('-')
    action = params[2]
    tutorial_name = params[1]

    if action == 'end':
        user.tutorial[tutorial_name]['stauts'] = 'done'
        user.save()

        return cb.message.edit(user.choice_localized(f'tutorial-{tutorial_name}-end'))

    if action == 'continue':
        user.tutorial[tutorial_name]['step'] += 1

    if action == 'back':
        user.tutorial[tutorial_name]['step'] -= 1

    user.save()
    cb.message.edit(user.get_tutorial_text(tutorial_name), reply_markup=markup_tutorial(user, tutorial_name))


def start_turorial(cli, user, tutorial_name, step=None):
    if not step:
        step = 1

    tutorial = user.tutorial

    if tutorial_name in tutorial:
        tutorial[tutorial_name]['step'] = step

    else:
        user.tutorial[tutorial_name] = dict(step=1, status='in processing')

    user.save()
    txt = user.get_tutorial_text(tutorial_name, step)

    cli.send_message(user.id, txt, reply_markup=markup_tutorial(user, tutorial_name))
