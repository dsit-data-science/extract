# Stage 1: Builder
FROM python:3.12-slim AS builder

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.2 && \
    pip install --no-cache-dir virtualenv==20.24.7

# Set working directory
WORKDIR /app

# Copy dependency files first
COPY pyproject.toml ./
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Install dependencies (without dev,doc)
RUN poetry install --without dev,doc

# Stage 2: Final runtime image
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1
# Set working directory
WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /app/.venv /app/.venv

# Copy app code
COPY ./consultation_emails ./consultation_emails
COPY ./app .
COPY ./README.md ./README.md

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"

# Expose Flask port
EXPOSE 5000

CMD ["python", "app.py"]
