FROM python:3.12-slim

RUN groupadd -r botuser && useradd -r -g botuser botuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ bot/
COPY runbooks/ runbooks/

RUN mkdir -p data && chown -R botuser:botuser /app

USER botuser

CMD ["python", "-m", "bot.main"]
