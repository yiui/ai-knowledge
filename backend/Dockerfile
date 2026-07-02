FROM python:3.12-slim-bookworm

WORKDIR /app

RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        libxcb1 \
        libglib2.0-0 \
        libgl1 \
        libgomp1 \
        poppler-utils && \
    rm -rf /var/lib/apt/lists/*

# 配置 pip 国内源（关键）
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.trusted-host mirrors.aliyun.com

COPY pyproject.toml .

RUN python - <<'PY'
import tomllib
from subprocess import check_call

with open("pyproject.toml", "rb") as f:
    deps = tomllib.load(f)["project"]["dependencies"]

check_call([
    "pip",
    "install",
    "--no-cache-dir",
    "--default-timeout=1000",
    *deps
])
PY

COPY app ./app

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]