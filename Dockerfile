FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY sentry_adapter/ sentry_adapter/

RUN pip install --no-cache-dir -e . && \
    python -m spacy download en_core_web_lg

COPY adapter.yaml.example adapter.yaml.example

ENV ADAPTER_CONFIG=/app/adapter.yaml

EXPOSE 8090

CMD ["sentry-adapter"]
