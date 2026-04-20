FROM python:3.11-slim

WORKDIR /app

# Systemabhängigkeiten (falls nötig)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# cloudflared Linux-Binary herunterladen
RUN curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
    -o /usr/local/bin/cloudflared \
    && chmod +x /usr/local/bin/cloudflared \
    && cloudflared --version

# Abhängigkeiten kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App-User anlegen fuer mehr Sicherheit (kein Root)
RUN useradd -m -u 1000 mercatoruser
RUN chown -R mercatoruser:mercatoruser /app

# Den Rest kopieren wir ins Image
COPY . .
RUN chown -R mercatoruser:mercatoruser /app

USER mercatoruser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "streamlit_app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
