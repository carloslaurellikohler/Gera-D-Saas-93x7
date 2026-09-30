"""CLI para rodar o motor manualmente, sem backend.

Exemplo:
    python -m gera_d_engine.cli analyze \\
        --input ../docs/exemplo1.docx \\
        --cs-name "Alexandre Marques" \\
        --pb-name "Francibele Ratzlaff" \\
        --interaction-type "Onboarding / Boas-vindas" \\
        --out-dir output
"""

from __future__ import annotations

import argparse
import re
import sys
import uuid
from datetime import date
from pathlib import Path

from gera_d_engine.calibration import load_calibration
from gera_d_engine.config import get_settings
from gera_d_engine.ingestion import load_transcript
from gera_d_engine.pipeline import run_pipeline
from gera_d_engine.rendering import export_both
from gera_d_engine.schemas.transcript import InputMetadata
from gera_d_engine.storage import JsonFileReportRepository


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "sem_nome"


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gera-d-engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Roda o pipeline completo sobre um input.")
    analyze.add_argument("--input", required=True, help="Caminho para .docx, .txt, .mp3 ou .mp4")
    analyze.add_argument("--cs-id")
    analyze.add_argument("--cs-name", required=True)
    analyze.add_argument("--pb-id")
    analyze.add_argument("--pb-name", required=True)
    analyze.add_argument("--interaction-id")
    analyze.add_argument("--interaction-date")
    analyze.add_argument("--interaction-type", required=True)
    analyze.add_argument("--duration")
    analyze.add_argument("--out-dir", default="output")

    return parser


def _cmd_analyze(args: argparse.Namespace) -> int:
    settings = get_settings()
    calibration = load_calibration()

    metadata = InputMetadata(
        cs_id=args.cs_id or _slugify(args.cs_name),
        cs_name=args.cs_name,
        pb_id=args.pb_id or _slugify(args.pb_name),
        pb_name=args.pb_name,
        interaction_id=args.interaction_id or uuid.uuid4().hex[:12],
        interaction_date=args.interaction_date or date.today().isoformat(),
        interaction_type=args.interaction_type,
        duration=args.duration,
    )

    print(f"[1/3] Ingerindo transcrição de {args.input}...", file=sys.stderr)
    transcript = load_transcript(args.input, settings)

    print("[2/3] Rodando pipeline de análise (etapas 2-8)...", file=sys.stderr)
    result = run_pipeline(transcript, metadata, settings=settings, calibration=calibration)

    out_dir = Path(args.out_dir)
    repo = JsonFileReportRepository(out_dir / "interactions")
    json_path = repo.save(result)
    print(f"[3/3] JSON salvo em {json_path}", file=sys.stderr)

    executivo_path, detalhado_path = export_both(result, calibration, out_dir / "reports")
    print(f"PDF Executivo: {executivo_path}", file=sys.stderr)
    print(f"PDF Detalhado: {detalhado_path}", file=sys.stderr)

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    if args.command == "analyze":
        return _cmd_analyze(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
