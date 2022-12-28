FROM python:3.8
FROM continuumio/miniconda3:latest

# Install system dependencies
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
&& rm -rf /var/lib/apt/lists/*

# Create and activate a new virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN mkdir diart
WORKDIR /diart/src/diart

# Copy the application files
COPY . .

# Install diart and its dependencies
RUN pip install diart pyannote-audio soundfile flask flask-cors ffmpeg

RUN conda create -n diart python=3.8
RUN conda install portaudio
RUN conda install pysoundfile -c conda-forge

# Set the default command to run when the container starts
CMD ["python", "app.py", "microphone"]
