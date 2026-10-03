web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn finance_project.wsgi --bind 0.0.0.0:$PORT --log-file -
