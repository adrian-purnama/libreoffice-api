FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

# Install Python + LibreOffice
RUN apt-get update && \
    apt-get install -y python3 python3-pip libreoffice && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 5000

CMD ["python3", "app.py"]
