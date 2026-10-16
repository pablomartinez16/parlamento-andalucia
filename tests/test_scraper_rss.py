try:
    import pytest
except ImportError:
    pytest = None
from app.scrapers.rss import RSSScraper

SAMPLE_RSS = """<?xml version="1.0" encoding="ISO-8859-1" ?>
<rss version="2.0">
<channel>
<title>Iniciativas en tramitación</title>
<item>
    <title><![CDATA[13-26/PPL-000002. Proposición de Ley sobre acoso escolar]]></title>
    <link><![CDATA[https://www.parlamentodeandalucia.es/portipo.do?numexp=13-26/PPL-000002]]></link>
    <pubDate>Tue, 8 Sep 2026 09:00:00 +0200</pubDate>
</item>
<item>
    <title><![CDATA[12-25/PL-000011. Ley de Patrimonio Cultural]]></title>
    <link><![CDATA[https://www.parlamentodeandalucia.es/portipo.do?numexp=12-25/PL-000011]]></link>
    <pubDate>Wed, 9 Sep 2026 10:00:00 +0200</pubDate>
</item>
</channel>
</rss>
"""


def test_parse_rss_items():
    scraper = RSSScraper()
    items = scraper._parse_items(SAMPLE_RSS, feed_type="iniciativas")

    assert len(items) == 2
    assert items[0]["expediente"] == "13-26/PPL-000002"
    assert "acoso escolar" in items[0]["titulo"]
    assert items[0]["tipo_feed"] == "iniciativas"
    assert items[1]["expediente"] == "12-25/PL-000011"
