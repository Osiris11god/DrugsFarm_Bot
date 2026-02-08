FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for python-telegram-bot and httpx
RUN apt-get update && apt-get install -y \
    libffi-dev \
    libssl-dev \
    libbz2-dev \
    liblzma-dev \
    zlib1g-dev \
    libreadline-dev \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
