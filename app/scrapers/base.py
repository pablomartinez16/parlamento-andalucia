import asyncio
import time
from typing import Optional, Dict
import httpx
from app.config import settings


class BaseScraper:
    """
    Base scraper with ethical scraping standards:
    - Custom descriptive User-Agent with contact info
    - Mandatory rate limiting between consecutive requests
    - Graceful error handling and timeouts
    - Encoding management (specifically latin1/ISO-8859-1 for Andalusian Parliament)
    """

    def __init__(
        self,
        rate_limit_seconds: Optional[float] = None,
        timeout: Optional[float] = None
    ):
        self.rate_limit_seconds = rate_limit_seconds or settings.SCRAPE_RATE_LIMIT_SECONDS
        self.timeout = timeout or settings.REQUEST_TIMEOUT_SECONDS
        self._last_request_time: float = 0.0
        self.headers: Dict[str, str] = {
            "User-Agent": settings.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        }

    async def _wait_rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_seconds:
            await asyncio.sleep(self.rate_limit_seconds - elapsed)
        self._last_request_time = time.time()

    async def fetch(self, url: str, encoding: str = "latin1") -> str:
        await self._wait_rate_limit()
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, verify=False) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            # The Parliament servers emit headers claiming ISO-8859-1 / latin1
            return response.content.decode(encoding, errors="replace")

    async def fetch_bytes(self, url: str) -> bytes:
        await self._wait_rate_limit()
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, verify=False) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.content
