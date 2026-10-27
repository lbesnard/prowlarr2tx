FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PROWLARR2TX_CONFIG_DIR=/config \
    PROWLARR2TX_STATE_DIR=/state \
    PROWLARR2TX_LOG_DIR=/logs

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} app && useradd -u ${UID} -g ${GID} -m app \
    && mkdir -p /config /state /logs && chown app:app /state /logs
USER app

VOLUME ["/config", "/state", "/logs"]
ENTRYPOINT ["prowlarr2tx"]
CMD ["daemon"]
