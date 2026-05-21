FROM python:3.13-slim

# 1. install WeasyPrint/PDF, curl for healthcheks
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libffi-dev \
    shared-mime-info \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 2. install poetry. Setup without .venv inside Docker
RUN pip install --no-cache-dir "poetry>=2.0.0" \
    && poetry config virtualenvs.create false

WORKDIR /app

# 4. copy dependencies files
COPY pyproject.toml poetry.lock* ./

# 5. install dependencies pockets
RUN poetry install --no-interaction --no-ansi --no-root

# 6. copy project source code
COPY . .
