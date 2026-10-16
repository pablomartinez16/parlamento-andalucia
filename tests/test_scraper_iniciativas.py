try:
    import pytest
except ImportError:
    pytest = None
from app.scrapers.iniciativas import IniciativaScraper

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<body>
<dl class="row mt-3 ml-1">
<dt class="col-sm-4">Fecha creación:</dt>
<dd class="col-sm-8">08/09/2026</dd>
<dt class="col-sm-4">Número de registro:</dt>
<dd class="col-sm-8">132603737</dd>
<dt class="col-sm-4">Proponente:</dt>
<dd class="col-sm-8">G.P. Por Andalucía</dd>
<dt class="col-sm-4">Extracto:</dt>
<dd class="col-sm-8">Proposición de Ley relativa a acoso y ciberacoso escolar en centros de Andalucía</dd>
<dt class="col-sm-4">Procedimiento:</dt>
<dd class="col-sm-8">Ordinario</dd>
<dt class="col-sm-4">Estado:</dt>
<dd class="col-sm-8">En tramitación</dd>
<dt class="col-sm-4">Tipo:</dt>
<dd class="col-sm-8">Proposiciones de Ley</dd>
</dl>

<h2>Listas de trámites</h2>
<dl class="ml-2">
<dt class="float-left mr-2">Fecha:</dt><dd class="mb-0">08/09/2026</dd>
<dt class="float-left mr-2">Número de registro:</dt><dd class="mb-0">132603750</dd>
<dt class="float-left mr-2">Descripción:</dt><dd class="mb-0">RE. Documentación complementaria</dd>
<div class="sep"><hr /></div>
<dt class="float-left mr-2">Fecha:</dt><dd class="mb-0">21/09/2026</dd>
<dt class="float-left mr-2">Descripción:</dt><dd class="mb-0">Publicación de la Proposición de Ley</dd>
<a href="/webdinamica/portal-web-parlamento/pdf.do?tipodoc=bopa&id=205114">BOPA nÂº 40 - 21/09/2026</a>
<div class="sep"><hr /></div>
</dl>
</body>
</html>
"""


def test_parse_iniciativa_html():
    scraper = IniciativaScraper()
    exp = "13-26/PPL-000002"
    url = f"https://example.com/portipo.do?numexp={exp}"
    data = scraper.parse_html(SAMPLE_HTML, exp, url)

    assert data["expediente"] == "13-26/PPL-000002"
    assert data["legislatura_numero"] == 13
    assert data["proponente"] == "G.P. Por Andalucía"
    assert data["estado"] == "En tramitación"
    assert data["tipo"] == "Proposiciones de Ley"
    assert data["numero_registro"] == "132603737"
    assert "acoso y ciberacoso" in data["titulo"]
    
    # Tramites validation
    assert len(data["tramites"]) >= 2
    assert "Documentación complementaria" in data["tramites"][0]["descripcion"]

    # Documents validation (verifying Mojibake 'nÂº' was cleaned to 'nº')
    assert len(data["documentos"]) == 1
    assert data["documentos"][0]["tipo"] == "BOPA"
    assert data["documentos"][0]["doc_id"] == "205114"
    assert "nÂº" not in data["documentos"][0]["titulo"]
    assert "nº" in data["documentos"][0]["titulo"]
    assert "https://www.parlamentodeandalucia.es" in data["documentos"][0]["url"]
