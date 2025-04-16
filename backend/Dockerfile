# Use a specific, slim Python version
FROM python:3.11-slim

WORKDIR /app

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies if any are needed (e.g., for psycopg2 build)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies using uv (faster than pip)
COPY pyproject.toml uv.lock* ./
# Install uv itself, then upgrade pip, then install project deps + gunicorn
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache --upgrade pip && \
    uv pip install --system --no-cache -r pyproject.toml gunicorn

# Copy project code into the container
COPY . .

# Set static files path (adjust if needed) and collect static files
# Only uncomment if Django needs to serve some static files itself,
# usually Nginx handles frontend static files.
# ENV STATIC_ROOT /app/staticfiles
# RUN python manage.py collectstatic --noinput --clear

# Expose the port Gunicorn will run on
EXPOSE 8000

# Run Gunicorn
# Ensure 'course_api.config.wsgi:application' matches your actual WSGI application path
# Increase workers based on server resources if needed (e.g., --workers=4)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "course_api.config.wsgi:application"]
