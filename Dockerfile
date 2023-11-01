# Use an official Python runtime as a parent image
FROM python:3.8

# Set the working directory to /app
WORKDIR /app

# Copy your script to the container
COPY your_script.py /app/

# Keep the container running
CMD ["tail", "-f", "/dev/null"]


# Use an official Python runtime as a parent image
FROM python:3.8

# Set the working directory to /app
WORKDIR /app

RUN pip install torchaudio==2.1.0
RUN pip install audiocraft==1.0.0
RUN pip install xformers== 0.0.22

# Copy your script to the container
COPY your_script.py /app/


# Keep the container running
CMD ["python", "your_script.py"]