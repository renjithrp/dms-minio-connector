# syntax=docker/dockerfile:1

FROM python:3.8-slim-buster

RUN ls -l
# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
 && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /python-docker

# Copy and install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files into the container
COPY . .

# Set the default command to run your application
CMD ["python", "main.py"]

# Expose the port the app runs on
EXPOSE 9082