"""BigQuery access helpers."""

from __future__ import annotations

import logging
from typing import Any

from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import GoogleAuthError
from google.cloud import bigquery

logger = logging.getLogger(__name__)


class BigQueryRepositoryError(RuntimeError):
    """Raised when BigQuery queries cannot be executed."""


class BigQueryRepository:
    """Small BigQuery query helper for dashboard and API reads."""

    def __init__(
        self,
        project_id: str,
        *,
        location: str | None = None,
        client: bigquery.Client | None = None,
    ) -> None:
        self.project_id = project_id
        self.location = location
        self.client = client or bigquery.Client(project=project_id, location=location)

    def query(
        self,
        sql: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Run a parameterized read query against BigQuery."""

        query_parameters = _query_parameters(parameters or {})
        job_config = bigquery.QueryJobConfig(query_parameters=query_parameters)
        logger.info(
            "Running BigQuery query project=%s location=%s sql_length=%d parameters=%s",
            self.project_id,
            self.location,
            len(sql),
            sorted((parameters or {}).keys()),
        )
        try:
            result = self.client.query(sql, job_config=job_config).result()
            return [dict(row.items()) for row in result]
        except (GoogleAPIError, GoogleAuthError, OSError) as exc:
            logger.exception("BigQuery query failed project=%s", self.project_id)
            raise BigQueryRepositoryError(str(exc)) from exc


def _query_parameters(parameters: dict[str, Any]) -> list[bigquery.ScalarQueryParameter]:
    return [
        bigquery.ScalarQueryParameter(name, _parameter_type(value), value)
        for name, value in parameters.items()
    ]


def _parameter_type(value: Any) -> str:
    if isinstance(value, bool):
        return "BOOL"
    if isinstance(value, int):
        return "INT64"
    if isinstance(value, float):
        return "FLOAT64"
    return "STRING"
