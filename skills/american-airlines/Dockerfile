FROM python:3.12-slim

# Install system dependencies for Chromium and xvfb
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    xauth \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libx11-xcb1 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir patchright

# Install Patchright's Chromium
RUN patchright install chromium

WORKDIR /app
COPY scripts/check_balance.py .

# Persistent profile directory inside container
RUN mkdir -p /root/.aa-browser-profiles

ENTRYPOINT ["sh", "-c", "Xvfb :99 -screen 0 1280x800x24 -nolisten tcp &\nexport DISPLAY=:99\nsleep 1\npython3 /app/check_balance.py \"$@\"", "--"]
