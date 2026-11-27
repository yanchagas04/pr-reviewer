# Imagem publicada no GHCR pelo workflow publish-image.yml.
FROM python:3.12-slim-bookworm AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /bin/uv
WORKDIR /build
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY README.md ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM python:3.12-slim-bookworm
LABEL org.opencontainers.image.source="https://github.com/yanchagas04/pr-reviewer" \
      org.opencontainers.image.description="Agente verificador de Pull Request"
COPY --from=build /opt/venv /opt/venv
# Sem WORKDIR nem USER: o GitHub define o diretório e exige acesso ao workspace.
ENTRYPOINT ["/opt/venv/bin/pr-reviewer"]
