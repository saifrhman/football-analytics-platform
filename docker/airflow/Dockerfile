FROM apache/airflow:2.9.3-python3.11

USER root
WORKDIR /opt/airflow

USER airflow
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e .
