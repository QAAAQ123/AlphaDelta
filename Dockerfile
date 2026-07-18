FROM python:3.11-slim

# PostgreSQL 연결용 필수 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# requirements.txt를 복사하고 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 나머지 소스코드 복사
COPY . .