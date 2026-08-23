FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CAMPUSINTEL_TRANSPORT=streamable-http \
    CAMPUSINTEL_HOST=0.0.0.0 \
    CAMPUSINTEL_PORT=8000

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

EXPOSE 8000
USER 65532:65532
ENTRYPOINT ["campusintel-mcp"]

