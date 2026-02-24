FROM python:3.12-slim

# System dependencies for Firefox/Camoufox
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgtk-3-0 \
    libasound2 \
    libx11-xcb1 \
    libdbus-glib-1-2 \
    libxt6 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libpango-1.0-0 \
    libatk1.0-0 \
    libcairo2 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install camoufox
RUN pip3 install --no-cache-dir camoufox[geoip] orjson

# Fetch camoufox browser data (as root, before switching user)
RUN python3 -m camoufox fetch

# Upgrade Playwright Node.js driver to match @playwright/cli version
# (prevents "version mismatch: server v1.58 / client v1.59" error)
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    PW_DRIVER=/usr/local/lib/python3.12/site-packages/playwright/driver && \
    curl -sL https://registry.npmjs.org/playwright-core/-/playwright-core-1.59.0-alpha-1771104257000.tgz -o /tmp/pw.tgz && \
    cd /tmp && tar xzf pw.tgz && \
    rm -rf $PW_DRIVER/package && \
    mv /tmp/package $PW_DRIVER/package && \
    rm -f /tmp/pw.tgz && \
    apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Create non-root user (required for Camoufox on Linux)
RUN useradd -m -s /bin/bash cfox
# Copy camoufox data to user home
RUN mkdir -p /home/cfox/.cache && \
    cp -r /root/.cache/camoufox /home/cfox/.cache/camoufox && \
    chown -R cfox:cfox /home/cfox/.cache

WORKDIR /app
COPY launch_server.py .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

USER cfox
EXPOSE 9222

ENTRYPOINT ["/app/entrypoint.sh"]
