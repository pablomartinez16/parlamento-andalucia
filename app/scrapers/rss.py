import re
import warnings
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from app.scrapers.base import BaseScraper

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


class RSSScraper(BaseScraper):
    """
    Scraper for the official RSS feeds of the Parliament of Andalusia:
    - Iniciativas en tramitación
    - Leyes aprobadas
    - BOPA
    """

    BASE_RSS_URL = "https://www.parlamentodeandalucia.es/webdinamica/portal-web-parlamento/utilidades/sindicacionrss.do"

    async def get_iniciativas_feed(self) -> List[Dict[str, Any]]:
        """Fetch and parse new initiatives in progress."""
        url = f"{self.BASE_RSS_URL}?contenido=Iniciativas"
        xml_text = await self.fetch(url, encoding="latin1")
        return self._parse_items(xml_text, feed_type="iniciativas")

    async def get_leyes_feed(self) -> List[Dict[str, Any]]:
        """Fetch and parse approved laws feed."""
        url = f"{self.BASE_RSS_URL}?contenido=Leyes"
        xml_text = await self.fetch(url, encoding="latin1")
        return self._parse_items(xml_text, feed_type="leyes")

    async def get_bopa_feed(self) -> List[Dict[str, Any]]:
        """Fetch and parse BOPA official bulletin items."""
        url = f"{self.BASE_RSS_URL}?contenido=Bopa"
        xml_text = await self.fetch(url, encoding="latin1")
        return self._parse_bopa_items(xml_text)

    def _parse_items(self, xml_text: str, feed_type: str) -> List[Dict[str, Any]]:
        results = []
        soup = BeautifulSoup(xml_text, "html.parser") # or xml parser
        items = soup.find_all("item")

        for item in items:
            title_tag = item.find("title")
            link_tag = item.find("link")
            pub_date_tag = item.find("pubdate")

            title = title_tag.get_text(strip=True) if title_tag else ""
            link = link_tag.get_text(strip=True) if link_tag else ""
            pub_date_str = pub_date_tag.get_text(strip=True) if pub_date_tag else ""

            # Extract expediente from title or link
            # Patterns: 13-26/PPL-000002, 12-25/PL-000011
            exp_match = re.search(r'(\d{1,2}-\d{2}/[A-Z]+-\d{6})', title)
            if not exp_match and link:
                exp_match = re.search(r'numexp=([0-9a-zA-Z\-\/]+)', link)
            
            expediente = exp_match.group(1) if exp_match else None

            # Parse pub_date if possible
            pub_date = None
            if pub_date_str:
                try:
                    # e.g. "Tue, 8 Sep 2026 09:00:00 +0200"
                    dt = datetime.strptime(pub_date_str[:25].strip(), "%a, %d %b %Y %H:%M:%S")
                    pub_date = dt.date()
                except Exception:
                    pass

            if expediente:
                clean_title = re.sub(r'^\d{1,2}-\d{2}/[A-Z]+-\d{6}\.\s*', '', title).strip()
                results.append({
                    "expediente": expediente,
                    "titulo": self._clean_text(clean_title or title),
                    "link": link,
                    "fecha_publicacion": pub_date,
                    "tipo_feed": feed_type
                })

        return results

    def _parse_bopa_items(self, xml_text: str) -> List[Dict[str, Any]]:
        results = []
        soup = BeautifulSoup(xml_text, "html.parser")
        items = soup.find_all("item")

        for item in items:
            title_tag = item.find("title")
            link_tag = item.find("link")
            enclosure_tag = item.find("enclosure")
            pub_date_tag = item.find("pubdate")

            title = title_tag.get_text(strip=True) if title_tag else ""
            link = link_tag.get_text(strip=True) if link_tag else ""
            pdf_url = enclosure_tag.get("url") if enclosure_tag else link

            # Extract BOPA ID
            bopa_id_match = re.search(r'id=(\d+)', pdf_url or link)
            bopa_id = bopa_id_match.group(1) if bopa_id_match else None

            # Extract BOPA number
            num_match = re.search(r'n[úu]m\.\s*(\d+)', title, re.IGNORECASE)
            numero = num_match.group(1) if num_match else None

            results.append({
                "numero": numero,
                "id": bopa_id,
                "titulo": self._clean_text(title),
                "pdf_url": pdf_url,
                "link": link
            })

        return results

    @staticmethod
    def _clean_text(val: Optional[str]) -> str:
        if not val:
            return ""
        try:
            if "Â" in val or "Ã" in val:
                val = val.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
        val = val.replace("nÂº", "nº").replace("NÂº", "Nº")
        val = val.replace("Âº", "º").replace("Âª", "ª")
        val = val.replace("Â", "")
        return val.strip()
