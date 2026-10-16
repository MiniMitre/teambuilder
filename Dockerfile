
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       git nodejs npm ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY . .

# Install the Python project and its locked dependencies.
RUN uv sync --frozen \
    && uv pip install --python .venv/bin/python gunicorn

# Fetch the Pokémon data files used to build the database.
RUN git clone --filter=blob:none --no-checkout \
    https://github.com/projectpokemon/champout.git /app/champout \
    && cd /app/champout \
    && git sparse-checkout init --cone \
    && git sparse-checkout set parse \
    && git checkout main

# Fetch the calculator version documented by this project.
RUN git clone --filter=blob:none --no-checkout \
    https://github.com/smogon/damage-calc.git /app/damage-calc \
    && cd /app/damage-calc \
    && git sparse-checkout init --cone \
    && git sparse-checkout set calc \
    && git checkout e7fd7e59f3eef7ea42fba3c8b83261cb4a14109d

# Compile the calculator and install it for the Python wrapper.
RUN cd /app/damage-calc/calc \
    && npm install \
    && npm run compile \
    && cd /app \
    && npm install ./damage-calc/calc

# Generate the DuckDB database from the Pokémon data.
RUN uv run teambuilder build-db

EXPOSE 10000

CMD ["sh", "-c", "uv run gunicorn --bind 0.0.0.0:${PORT:-10000} teambuilder.web_server:app"]
