"""Responsible Transfermarkt scraping client."""

import hashlib
import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from football_intelligence.ingestion.base import IngestionClient, RawAsset

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class TransfermarktIngestionError(RuntimeError):
    """Raised when Transfermarkt collection fails unexpectedly."""


@dataclass(frozen=True)
class TransfermarktFetchFailure:
    """A graceful failure captured during Transfermarkt collection."""

    url: str
    reason: str


@dataclass(frozen=True)
class TransfermarktRawAsset(RawAsset):
    """Raw Transfermarkt asset with lineage metadata."""

    dataset: str = ""
    url: str = ""


class TransfermarktClient(IngestionClient):
    """Client for responsibly collecting public Transfermarkt pages.

    The client only fetches explicitly configured URLs. It applies a fixed delay
    between requests, sends a descriptive user agent, retries transient network
    failures, and records failed pages without stopping the whole run.
    """

    def __init__(
        self,
        base_url: str,
        user_agent: str,
        request_delay_seconds: float,
        *,
        squad_urls: Iterable[str] = (),
        transfer_urls: Iterable[str] = (),
        timeout_seconds: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.request_delay_seconds = request_delay_seconds
        self.squad_urls = tuple(squad_urls)
        self.transfer_urls = tuple(transfer_urls)
        self.timeout_seconds = timeout_seconds
        self.failures: list[TransfermarktFetchFailure] = []
        self._last_request_at = 0.0
        self._http_client = httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={**DEFAULT_HEADERS, "User-Agent": user_agent},
        )

    def fetch(self) -> Iterable[RawAsset]:
        """Yield raw HTML assets for configured squad and transfer URLs."""

        logger.info(
            "Starting Transfermarkt ingestion squad_urls=%d transfer_urls=%d delay=%.1fs",
            len(self.squad_urls),
            len(self.transfer_urls),
            self.request_delay_seconds,
        )

        for dataset, urls in (("squads", self.squad_urls), ("transfers", self.transfer_urls)):
            for url in urls:
                try:
                    html = self._fetch_html(url)
                except (TransfermarktIngestionError, httpx.HTTPError) as exc:
                    logger.warning(
                        "Skipping Transfermarkt URL after failure url=%s error=%s",
                        url,
                        exc,
                    )
                    self.failures.append(TransfermarktFetchFailure(url=url, reason=str(exc)))
                    continue

                yield TransfermarktRawAsset(
                    source="transfermarkt",
                    path=f"transfermarkt/raw_html/{dataset}/{_stable_url_id(url)}.html",
                    payload=html,
                    content_type="text/html; charset=utf-8",
                    dataset=dataset,
                    url=self._resolve_url(url),
                )

        logger.info("Finished Transfermarkt ingestion failures=%d", len(self.failures))

    def close(self) -> None:
        """Close underlying network resources."""

        self._http_client.close()

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, TransfermarktIngestionError)),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _fetch_html(self, url: str) -> bytes:
        self._respect_delay()
        resolved_url = self._resolve_url(url)
        logger.info("Fetching Transfermarkt page %s", resolved_url)
        response = self._http_client.get(resolved_url)

        if response.status_code in {403, 429}:
            raise TransfermarktIngestionError(
                f"Transfermarkt returned {response.status_code}; stop or increase delay"
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise TransfermarktIngestionError(
                f"Transfermarkt request failed {resolved_url}: {exc.response.status_code}"
            ) from exc

        return response.content

    def _respect_delay(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        sleep_seconds = self.request_delay_seconds - elapsed
        if sleep_seconds > 0:
            logger.debug("Sleeping %.2fs before next Transfermarkt request", sleep_seconds)
            time.sleep(sleep_seconds)
        self._last_request_at = time.monotonic()

    def _resolve_url(self, url: str) -> str:
        if url.startswith(("http://", "https://")):
            return url
        return urljoin(f"{self.base_url}/", url.lstrip("/"))


def _stable_url_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
