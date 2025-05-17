FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install Chromium, ChromiumDriver, and dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgdk-pixbuf2.0-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    wget unzip curl \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Chromium and driver paths
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Copy requirements and install Python dependencies
COPY requirements.txt Rebel_Assignment/requirements.txt
WORKDIR /Rebel_Assignment
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy your app code
COPY . /Rebel_Assignment

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
