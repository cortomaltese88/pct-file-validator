from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.config import load_config, resolve_profile
from core.sanitizer import analyze, sanitize


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gdlex-check", description="Validazione conservativa PCT/PDUA")
    parser.add_argument("input_folder", type=Path, help="File o cartella di input")
    parser.add_argument("--output", type=Path, help="Cartella output custom")
    parser.add_argument("--profile", default="pdua_safe", help="Profilo regole (default: pdua_safe)")
    parser.add_argument("--analyze", action="store_true", help="Esegue solo analisi")
    parser.add_argument("--sanitize", action="store_true", help="Corregge automaticamente e prepara output")
    parser.add_argument("--report", action="store_true", help="Mostra report sintetico su stdout")
    parser.add_argument("--strict", action="store_true", help="Exit code 2 se presenti warning")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--dry-run", action="store_true", help="Simula senza scrivere file")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config = load_config()
    profile = resolve_profile(config, args.profile)

    if args.sanitize:
        output_mode = "custom" if args.output else "sibling"
        output_dir, summary = sanitize(
            args.input_folder,
            profile,
            dry_run=args.dry_run,
            output_mode=output_mode,
            custom_output_dir=args.output,
        )
    else:
        summary = analyze(args.input_folder, profile)
        output_dir = None

    if args.json:
        payload = summary.to_dict()
        payload["output"] = str(output_dir) if output_dir else None
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for item in summary.files:
            print(f"{item.source} -> {item.status.upper()} [{item.correction_outcome}]")
        if output_dir:
            print(f"Output creato in: {output_dir}")

    if args.report and not args.json:
        print("\nReport sintetico:")
        for item in summary.files:
            for issue in item.issues:
                print(f"- {item.source.name} [{issue.level}] {issue.message}")

    if summary.has_errors:
        return 1
    if args.strict and any(item.status == "warning" for item in summary.files):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
