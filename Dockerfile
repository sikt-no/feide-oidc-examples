# NOTE: Use a Python 3.14 image when available in your environment.
# If your registry doesn't provide 3.14 yet, switch to the newest available 3.x image.
FROM python:3.14-rc-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN pip install --no-cache-dir -U pip \
  && pip install --no-cache-dir -e .

EXPOSE 8000

FROM base AS example
CMD ["python", "-m", "feide_login_full.app"]

FROM base AS simple
CMD ["python", "-m", "feide_login_simple.app"]

FROM base AS datasource
CMD ["python", "-m", "feide_data_source_api.app"]
