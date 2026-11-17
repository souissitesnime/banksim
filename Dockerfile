# Image de démonstration BankSim — NON construite ni testée dans l'environnement qui a généré le kit.
# Un seul worker : le verrou des mouvements d'argent est local au processus (ADR-04).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BANKSIM_ENV=production \
    BANKSIM_DATABASE_URL=sqlite:////data/banksim.db

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN useradd --system --uid 10001 banksim && mkdir /data && chown banksim /data
USER banksim
VOLUME ["/data"]
EXPOSE 8000

# En production l'application refuse de démarrer sans BANKSIM_SECRET et BANKSIM_ADMIN_PASSWORD.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2).status == 200 else 1)"

CMD ["uvicorn", "app.asgi:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
