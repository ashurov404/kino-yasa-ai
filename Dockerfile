FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BLENDER_BIN=/usr/bin/blender \
    FOURD_HUMANS_DIR=/opt/4D-Humans \
    FOURD_HUMANS_PYTHON=python3 \
    FOURD_HUMANS_ENABLED=1 \
    BLENDER_ENABLED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    blender \
    ffmpeg \
    git \
    curl \
    ca-certificates \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 4D-Humans is intentionally kept separate from the application source.
# Its required SMPL model files are NOT bundled here because their license
# must be verified for commercial use before production deployment.
RUN git clone --depth 1 https://github.com/shubham-goel/4D-Humans.git /opt/4D-Humans

COPY . /app

RUN python -m py_compile /app/uzb_ai_bot3.py

EXPOSE 10000

CMD ["python", "uzb_ai_bot3.py"]
