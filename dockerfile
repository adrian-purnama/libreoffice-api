FROM debian:stable-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y libreoffice default-jre python3 python3-venv python3-pip && \
    apt-get clean

# Create app directory
WORKDIR /app

# Copy requirement file
COPY requirements.txt .

# Create virtual environment
RUN python3 -m venv /app/venv

# Install python deps inside venv
RUN /app/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 3501

# Start server using venv python
CMD ["/app/venv/bin/python", "server.py"]
