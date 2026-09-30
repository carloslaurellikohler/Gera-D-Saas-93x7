"""Etapa 9 (renderização) — HTML via Jinja2 + PDF via WeasyPrint.

Os dois relatórios (Executivo e Detalhado) são renderizados a partir do MESMO AnalysisResult,
garantindo consistência entre eles (mesma nota, mesma classificação, mesmo texto-base).
"""

from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from gera_d_engine.calibration import Calibration
from gera_d_engine.config import TEMPLATES_DIR
from gera_d_engine.rendering.view import build_view
from gera_d_engine.schemas.analysis import AnalysisResult

_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)

_TEMPLATES_BY_KIND = {
    "executivo": "executivo.html.j2",
    "detalhado": "detalhado.html.j2",
}


def _slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", text.lower())
    return text.strip("_") or "sem_nome"


def _base_css() -> str:
    return (TEMPLATES_DIR / "base.css").read_text(encoding="utf-8")


def render_html(result: AnalysisResult, calibration: Calibration, report_kind: str) -> str:
    if report_kind not in _TEMPLATES_BY_KIND:
        raise ValueError(f"report_kind inválido: {report_kind!r}. Use 'executivo' ou 'detalhado'.")
    template = _env.get_template(_TEMPLATES_BY_KIND[report_kind])
    view = build_view(result, calibration)
    return template.render(base_css=_base_css(), **view)


def report_filename(result: AnalysisResult, report_kind: str) -> str:
    return (
        f"{_slugify(result.cs_name)}_{_slugify(result.pb_name)}_"
        f"{report_kind}_{result.interaction_id}.pdf"
    )


def export_pdf(
    result: AnalysisResult, calibration: Calibration, report_kind: str, out_dir: str | Path
) -> Path:
    html_content = render_html(result, calibration, report_kind)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / report_filename(result, report_kind)
    HTML(string=html_content, base_url=str(TEMPLATES_DIR)).write_pdf(str(out_path))
    return out_path


def export_both(
    result: AnalysisResult, calibration: Calibration, out_dir: str | Path
) -> tuple[Path, Path]:
    executivo = export_pdf(result, calibration, "executivo", out_dir)
    detalhado = export_pdf(result, calibration, "detalhado", out_dir)
    return executivo, detalhado
