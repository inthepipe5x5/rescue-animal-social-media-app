# Use the official Python image from the Docker Hub
FROM python:3.8-alpine

# Set environment variables to prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
RUN apk update && apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    postgresql-dev \
    build-base \
    python3-dev \
    py3-pip \
    jpeg-dev \
    zlib-dev

# Create and set the working directory
WORKDIR ${PROJECT_DIR}

# Copy the requirements file into the container
COPY requirements.txt ${PROJECT_DIR}/

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r ${PROJECT_DIR}/requirements.txt

# Copy the rest of the application code into the container
COPY Project ${PROJECT_DIR}/Project

# Set the PYTHONPATH environment variable
ENV PYTHONPATH="${PROJECT_DIR}:${PYTHONPATH}"

# Expose the port the app runs on
EXPOSE 10000

# Define the command to run the application using Gunicorn
CMD ["gunicorn", "Project.core.app:create_app", "--workers", "4", "--bind", "0.0.0.0:10000"]