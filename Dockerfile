FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy all code
COPY . /app/

# Install python dependencies for all agents
# We use || true in case some requirements.txt files are missing or have errors, 
# but they should ideally all pass.
RUN pip install --no-cache-dir -r agents/crawler/requirements.txt
RUN pip install --no-cache-dir -r agents/test_generator/requirements.txt
RUN pip install --no-cache-dir -r agents/playwright_gen/requirements.txt
RUN pip install --no-cache-dir -r agents/cicd/requirements.txt
RUN pip install --no-cache-dir -r agents/triage_engine/requirements.txt

# Install Playwright browsers (required by Playwright Gen and CICD)
RUN pip install playwright
RUN playwright install --with-deps chromium

# Copy Nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Setup Supervisor config
# We copy it to the location supervisor expects
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose the port (Hugging Face expects 7860, Render uses PORT)
EXPOSE 7860

# Create a startup script to handle dynamic PORT injection and start supervisor
RUN echo '#!/bin/bash\n\
sed -i "s/listen 8000;/listen ${PORT:-7860};/g" /app/nginx.conf\n\
/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf\n\
' > /app/start.sh && chmod +x /app/start.sh

# Start using the wrapper script
CMD ["/app/start.sh"]
