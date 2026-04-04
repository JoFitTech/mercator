FROM python:3.11-slim

WORKDIR /app

# Systemabhängigkeiten (falls nötig)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Abhängigkeiten kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Den Rest kopieren wir per Volume in der Compose-Datei für die Entwicklung,
# aber wir können ihn auch hierher kopieren für ein fertiges Image.
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
