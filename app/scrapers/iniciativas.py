import re
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper


class IniciativaScraper(BaseScraper):
    """
    Scraper for individual initiative detail pages.
    Parses metadata (dl/dt/dd) and the list of procedural steps (trámites) + PDF links.
    """

    BASE_URL = "https://www.parlamentodeandalucia.es/webdinamica/portal-web-parlamento/actividadparlamentaria/todaslasiniciativas/portipo.do"

    async def get_iniciativa(self, expediente: str) -> Optional[Dict[str, Any]]:
        """
        Fetch and parse full initiative details for a given expediente (e.g. 13-26/PPL-000002).
        Returns None if not found or empty.
        """
        url = f"{self.BASE_URL}?numexp={expediente}"
        html = await self.fetch(url, encoding="latin1")

        if "<dl class=\"row mt-3 ml-1\">" not in html and "Extracto:" not in html:
            return None

        return self.parse_html(html, expediente, url)

    def parse_html(self, html: str, expediente: str, url: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        
        # 1. Main Metadata Block
        metadata: Dict[str, str] = {}
        main_dl = soup.find("dl", class_=re.compile(r"row.*mt-3"))
        if main_dl:
            dts = main_dl.find_all("dt")
            for dt in dts:
                dd = dt.find_next_sibling("dd")
                if dd:
                    key = dt.get_text(strip=True).rstrip(":")
                    val = dd.get_text(strip=True)
                    metadata[key.lower()] = val

        # Clean/extract specific fields
        fecha_str = metadata.get("fecha creación") or metadata.get("fecha creacion") or metadata.get("fecha")
        fecha_creacion: Optional[date] = None
        if fecha_str:
            try:
                fecha_creacion = datetime.strptime(fecha_str.strip(), "%d/%m/%Y").date()
            except ValueError:
                pass

        # Extract legislature from expediente: "13-26/PPL-000002" -> 13
        leg_num = 13
        leg_match = re.match(r"^(\d+)-", expediente)
        if leg_match:
            try:
                leg_num = int(leg_match.group(1))
            except ValueError:
                pass

        tipo = metadata.get("tipo") or "Iniciativa"
        extracto = metadata.get("extracto") or ""
        titulo = extracto or metadata.get("título") or expediente
        proponente = metadata.get("proponente")
        estado = metadata.get("estado") or "Desconocido"
        procedimiento = metadata.get("procedimiento")
        num_registro = metadata.get("número de registro") or metadata.get("numero de registro")

        # 2. Tramites & Attached Documents
        tramites: List[Dict[str, Any]] = []
        documentos: List[Dict[str, Any]] = []

        # Find "Listas de trámites" section
        h2 = soup.find(lambda tag: tag.name in ["h2", "h3"] and "trámites" in tag.get_text().lower())
        if h2:
            tramites_dl = h2.find_next_sibling("dl")
            if tramites_dl:
                # Sections are separated by <div class="sep"> or hr
                # Let's parse items by grouping dts/dds
                current_tramite: Dict[str, Any] = {}
                for element in tramites_dl.children:
                    if element.name == "dt":
                        dt_text = element.get_text(strip=True).rstrip(":").lower()
                        dd = element.find_next_sibling("dd")
                        dd_text = dd.get_text(strip=True) if dd else ""
                        
                        if "fecha" in dt_text:
                            current_tramite["fecha"] = dd_text
                        elif "descripción" in dt_text or "descripcion" in dt_text:
                            current_tramite["descripcion"] = dd_text
                        elif "registro" in dt_text:
                            current_tramite["numero_registro"] = dd_text
                        elif "órgano" in dt_text or "organo" in dt_text:
                            current_tramite["organo"] = dd_text
                        elif "sesión" in dt_text or "sesion" in dt_text:
                            current_tramite["sesion"] = dd_text
                            
                    elif element.name == "div" and "sep" in element.get("class", []):
                        if current_tramite.get("descripcion") or current_tramite.get("fecha"):
                            self._commit_tramite(current_tramite, tramites)
                            current_tramite = {}

                if current_tramite.get("descripcion") or current_tramite.get("fecha"):
                    self._commit_tramite(current_tramite, tramites)

        # 3. Document links (BOPA & Diarios)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if "tipodoc=bopa" in href:
                id_match = re.search(r'id=(\d+)', href)
                doc_id = id_match.group(1) if id_match else None
                full_url = f"https://www.parlamentodeandalucia.es{href}" if href.startswith("/") else href
                documentos.append({
                    "tipo": "BOPA",
                    "titulo": text or "Boletín Oficial (BOPA)",
                    "url": full_url,
                    "doc_id": doc_id
                })
            elif "tipodoc=diario" in href:
                id_match = re.search(r'id=(\d+)', href)
                doc_id = id_match.group(1) if id_match else None
                full_url = f"https://www.parlamentodeandalucia.es{href}" if href.startswith("/") else href
                documentos.append({
                    "tipo": "DIARIO",
                    "titulo": text or "Diario de Sesiones",
                    "url": full_url,
                    "doc_id": doc_id
                })

        def clean_text(val: Optional[str]) -> str:
            if not val:
                return ""
            # Reconstruct double-encoded UTF-8 as Latin1/Windows-1252 if present
            try:
                if "Â" in val or "Ã" in val:
                    val = val.encode("latin1").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
            # Specific replacement for masculine/feminine ordinal and common mojibake sequences
            val = val.replace("nÂº", "nº").replace("NÂº", "Nº")
            val = val.replace("Âº", "º").replace("Âª", "ª")
            val = val.replace("Â", "")
            return val.strip()

        # Deduplicate documentos by URL and clean titles
        seen_urls = set()
        unique_docs = []
        for doc in documentos:
            if doc["url"] not in seen_urls:
                seen_urls.add(doc["url"])
                doc["titulo"] = clean_text(doc["titulo"])
                unique_docs.append(doc)

        return {
            "expediente": expediente,
            "legislatura_numero": leg_num,
            "titulo": clean_text(titulo),
            "extracto": clean_text(extracto),
            "tipo": clean_text(tipo),
            "proponente": clean_text(proponente),
            "estado": clean_text(estado),
            "procedimiento": clean_text(procedimiento),
            "numero_registro": num_registro,
            "fecha_creacion": fecha_creacion,
            "url_ficha": url,
            "tramites": tramites,
            "documentos": unique_docs
        }

    def _commit_tramite(self, raw: Dict[str, Any], tramites_list: List[Dict[str, Any]]) -> None:
        fecha_obj = None
        if raw.get("fecha"):
            try:
                fecha_obj = datetime.strptime(raw["fecha"].strip(), "%d/%m/%Y").date()
            except ValueError:
                pass

        tramites_list.append({
            "fecha": fecha_obj,
            "numero_registro": raw.get("numero_registro"),
            "descripcion": raw.get("descripcion", ""),
            "organo_tramitador": raw.get("organo"),
            "sesion": raw.get("sesion"),
        })
