"""BigQuery access helpers."""

import logging

logger = logging.getLogger(__name__)


class BigQueryRepository:
    """Placeholder repository for curated warehouse reads and loads."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id

    def query(self, sql: str) -> list[dict[str, object]]:
        """Run a read query against BigQuery.

        The implementation will be added alongside API and dashboard data contracts.
        """

        logger.info(
            "BigQuery query placeholder project=%s sql_length=%d",
            self.project_id,
            len(sql),
        )
        return []
