# Use official Python image
FROM python:3.11-slim

# Prevent .pyc files and unbuffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the entire project
COPY . .

# Set working directory
WORKDIR /app/football_tournament

# Collect static files
RUN python manage.py collectstatic --noinput
RUN python manage.py migrate
RUN python manage.py checksuperuser || python manage.py createsuperuser

# Set environment port for Fly
ENV PORT=8080

# Run Gunicorn to serve the Django app
CMD ["gunicorn", "football_tournament.wsgi:application", "--bind", "0.0.0.0:8080"]
