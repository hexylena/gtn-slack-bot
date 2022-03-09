python manage.py migrate
python manage.py collectstatic --no-input
# Freshest possible
curl https://gallantries.github.io/video-library/api/videos.json > api/videos.json
curl https://gallantries.github.io/video-library/api/sessions.json > api/sessions.json
