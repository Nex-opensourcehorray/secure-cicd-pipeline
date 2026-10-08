FROM python:3.14.7-slim-trixie AS builder

WORKDIR /build

COPY requirements.txt ./

RUN python -m venv /opt/venv \
    && /opt/venv/bin/python -m pip install --no-cache-dir --disable-pip-version-check -r requirements.txt \
    && /opt/venv/bin/python -m pip uninstall --yes pip setuptools \
    && rm -rf /opt/venv/lib/python3.14/site-packages/pip* \
        /opt/venv/lib/python3.14/site-packages/setuptools*

FROM python:3.14.7-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN python -m pip uninstall --yes pip setuptools \
    && rm -rf /usr/local/lib/python3.14/ensurepip \
        /usr/local/lib/python3.14/site-packages/pip* \
        /usr/local/lib/python3.14/site-packages/setuptools* \
    && groupadd --gid 10001 appgroup \
    && useradd --uid 10001 --gid appgroup --no-create-home --shell /usr/sbin/nologin appuser

COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser:appgroup app/ ./app/

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).close()"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
