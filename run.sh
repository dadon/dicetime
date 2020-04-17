./manage.py webhook
screen -S dice -dm gunicorn --access-logfile gunicorn.log --workers 24 --bind 127.0.0.1:8000 --pid gunicorn.pid dice_time.wsgi:application
screen -S jobs -dm ./manage.py startjobs
screen -ls
