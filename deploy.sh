#!/bin/bash

# Load environment variables from top-level .env
set -a
source ../.env
set +a

# Frontend deployment
cd frontend
npm install
npm run build
rsync -avz --delete out/ $DEPLOY_USER@$DEPLOY_HOST:$FRONTEND_PATH/

# Backend deployment
cd ../backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
DJANGO_SETTINGS_MODULE=course_api.settings.production python manage.py migrate

# Collect static files
DJANGO_SETTINGS_MODULE=course_api.settings.production python manage.py collectstatic --noinput

# Update Gunicorn service environment
sudo -E bash -c 'cat > /etc/systemd/system/gunicorn.service << EOL
[Unit]
Description=gunicorn daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory='$BACKEND_PATH'
EnvironmentFile='$ENV_FILE_PATH'
ExecStart='$BACKEND_PATH'/venv/bin/gunicorn \
    --access-logfile - \
    --workers 3 \
    --bind unix:/run/gunicorn.sock \
    course_api.wsgi:application \
    --env DJANGO_SETTINGS_MODULE=course_api.settings.production

[Install]
WantedBy=multi-user.target
EOL'

# Reload systemd and restart Gunicorn
sudo systemctl daemon-reload
sudo systemctl restart gunicorn