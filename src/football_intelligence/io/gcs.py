"""GCS bronze/silver/gold storage helpers."""

import logging

logger = logging.getLogger(__name__)


class GCSObjectWriter:
    """Placeholder writer for persisting raw and curated assets to GCS."""

    def __init__(self, bucket_name: str) -> None:
        self.bucket_name = bucket_name

    def write_bytes(self, object_name: str, payload: bytes, content_type: str) -> None:
        """Write bytes to a GCS object path.

        The implementation will be added once bronze ingestion contracts are defined.
        """

        logger.info(
            "GCS write placeholder bucket=%s object=%s content_type=%s bytes=%d",
            self.bucket_name,
            object_name,
            content_type,
            len(payload),
        )
