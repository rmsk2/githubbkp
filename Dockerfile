FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .
COPY app.py .
COPY gschmarri.py .
COPY ghclient.py .
COPY private-tls-ca.pem .

RUN pip install -r requirements.txt

CMD ["python", "app.py"]