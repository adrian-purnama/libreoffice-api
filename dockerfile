FROM debian:stable-slim

# Install LibreOffice + Java
RUN apt-get update && \
    apt-get install -y libreoffice default-jre python3 python3-pip && \
    apt-get clean

# Install Flask & dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3501
CMD ["python3", "server.py"]
