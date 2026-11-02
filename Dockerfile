# The API (and the engine behind it). The static UI is served by nginx, see docker-compose.yml.
FROM python:3.12-slim
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src/ src/
RUN uv sync --frozen --no-dev --extra ui --extra browser
RUN uv run playwright install --with-deps chromium
EXPOSE 8090
CMD ["uv", "run", "handrail", "ui", "--host", "0.0.0.0", "--port", "8090", "--capabilities", "/data/capabilities", "--evidence", "/data/evidence/runs", "--episodes", "/data/evidence/episodes.db", "--index", "/data/evidence/handrail.db"]
