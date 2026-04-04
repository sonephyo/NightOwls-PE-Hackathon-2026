FROM python:3.13-slim

# Install uv
RUN pip install uv --no-cache-dir

WORKDIR /app

# Install dependencies (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code and seed utilities
COPY app/ ./app/
COPY run.py seed.py load_seed.py ./
COPY data/ ./data/
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

EXPOSE 8000

CMD ["./entrypoint.sh"]
