# Use the official Python image as a base image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt requirements.txt

# Install dependencies
RUN pip install -r requirements.txt

# Copy the API code into the container
COPY app.py app.py

# Expose the port where the API will run
EXPOSE 5000

# Start the API when the container is run
CMD ["python", "app.py"]