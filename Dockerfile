# Dockerfile

FROM python:3.13-alpine3.21

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apk update && apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    postgresql-dev \
    python3-dev \
    cargo \
    jpeg-dev \
    zlib-dev \
    build-base \
    libxml2-dev \
    libxslt-dev \
    bash \
    curl

# Install pip dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the application code
COPY . .

# Run the app using gunicorn
CMD ["gunicorn", "watergo.wsgi:application", "--bind", "0.0.0.0:8000"]
