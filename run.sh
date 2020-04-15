gunicorn --reload --access-logfile gunicorn.log --workers 4 --bind 127.0.0.1:8000 --pid gunicorn.pid dice_time.wsgi:application
