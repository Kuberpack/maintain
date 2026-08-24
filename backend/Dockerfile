FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Documentation/default only -- the actual listening port is $PORT if the
# host sets one (Railway and most PaaS platforms assign this dynamically),
# falling back to 8000 for docker-compose and any other host that doesn't.
EXPOSE 8000

# No --reload here: that's a local-dev convenience (file-watching, paired
# with docker-compose.yml's bind mount), not something a production image
# should carry -- see that file's `backend.command` override for local dev.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
