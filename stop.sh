kill `grep -hs ^ gunicorn.pid`
screen -S jobs -X quit
screen -S dicebot -X quit
screen -S celery -X quit
