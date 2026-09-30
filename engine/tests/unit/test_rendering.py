from gera_d_engine.calibration import load_calibration
from gera_d_engine.rendering import export_both, render_html, report_filename
from tests.fixtures.sample_result import build_sample_result


def test_render_html_contains_key_sections():
    result = build_sample_result()
    calibration = load_calibration()

    executivo_html = render_html(result, calibration, "executivo")
    assert "VISÃO EXECUTIVA DA MONITORIA 93x7®" in executivo_html
    assert "Diagnóstico Executivo" in executivo_html
    assert "POSICIONAMENTO" in executivo_html
    # A régua de faixas deve ter sido aplicada (nenhuma nota "crua" sem farol/classe).
    assert 'class="farol excelente"' in executivo_html
    assert 'class="farol desenvolvimento_critico"' in executivo_html

    detalhado_html = render_html(result, calibration, "detalhado")
    assert "VISÃO DETALHADA DA MONITORIA 93x7®" in detalhado_html
    assert "Análise dos Critérios" in detalhado_html
    assert "Perguntas Sugeridas" in detalhado_html


def test_render_html_css_is_not_escaped():
    result = build_sample_result()
    calibration = load_calibration()
    html = render_html(result, calibration, "executivo")
    # A regra de rodapé (@page) depende de aspas literais no CSS — se o Jinja2 escapar
    # `"Documento confidencial."` para `&quot;...&quot;`, a regra quebra silenciosamente.
    assert '"Documento confidencial."' in html
    assert "&quot;" not in html


def test_report_filename_identifies_cs_pb_and_kind():
    result = build_sample_result()
    filename = report_filename(result, "executivo")
    assert filename == "alexandre_marques_francibele_ratzlaff_executivo_test-interaction-001.pdf"


def test_export_both_writes_two_pdf_files(tmp_path):
    result = build_sample_result()
    calibration = load_calibration()

    executivo_path, detalhado_path = export_both(result, calibration, tmp_path)

    assert executivo_path.exists()
    assert detalhado_path.exists()
    assert executivo_path.suffix == ".pdf"
    assert executivo_path.read_bytes()[:4] == b"%PDF"
    assert detalhado_path.read_bytes()[:4] == b"%PDF"
