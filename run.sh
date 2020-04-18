./manage.py webhook
screen -S celery -dm celery worker -A celery_app --concurrency=5
screen -S dice -dm gunicorn --access-logfile gunicorn.log --workers 8 --bind 127.0.0.1:8000 --pid gunicorn.pid dice_time.wsgi:application
screen -S jobs -dm ./manage.py startjobs
screen -ls
