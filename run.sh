gunicorn --access-logfile gunicorn.log --workers 8 --bind 127.0.0.1:8000 --pid gunicorn.pid dice_time.wsgi:application
python manage.py startjobs
