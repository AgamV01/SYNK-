# SYNK server image: FastAPI WebSocket runtime serving the tavern demo world.
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
COPY synk ./synk
COPY examples ./examples
RUN pip install --no-cache-dir .

EXPOSE 8000
# Override ALLOWED_ORIGINS in production to lock down browser origins.
ENV ALLOWED_ORIGINS=""
CMD ["uvicorn", "synk.server:app", "--host", "0.0.0.0", "--port", "8000"]
