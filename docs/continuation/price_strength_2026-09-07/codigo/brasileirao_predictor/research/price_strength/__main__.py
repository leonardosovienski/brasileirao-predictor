"""Offline CLI; imports neither collectors nor the production serving model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .artifacts import read_hashed, write_artifacts
from .demo import demo_inputs
from .quotes import scan_quotes
from .study import price_policy, run_study, timestamp


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pesquisa offline de preços e xG; sem apostas ou acesso operacional.")
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("scan", help="Comparar snapshots completos no horário informado")
    scan.add_argument("--quotes", type=Path, required=True)
    scan.add_argument("--policy", type=Path, required=True)
    scan.add_argument("--as-of", required=True)
    scan.add_argument("--output-dir", type=Path, required=True)
    study = commands.add_parser("study", help="Executar protocolo exploratório explícito com candidato xG independente")
    for name in ("protocol", "history", "fixtures", "quotes"):
        study.add_argument(f"--{name}", type=Path, required=True)
    study.add_argument("--baseline", type=Path, help="Previsões congeladas externas, sem ler modelo operacional")
    study.add_argument("--output-dir", type=Path, required=True)
    demo = commands.add_parser("demo", help="Demonstrar com dados fabricados, sem valor econômico")
    demo.add_argument("--output-dir", type=Path, required=True)
    return parser


def _load(inputs: dict[str, Path]) -> tuple[dict, dict]:
    content, hashes = {}, {}
    for name, path in inputs.items():
        content[name], hashes[name] = read_hashed(path, jsonl=name in {"history", "fixtures", "quotes", "baseline"})
    return content, hashes


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result: dict[str, object]
    try:
        if args.command == "demo":
            manufactured = demo_inputs()
            write_artifacts(
                args.output_dir,
                inputs={},
                artifacts=manufactured,
                metadata={"status": "SYNTHETIC_DEMONSTRATION", "profitability_established": False},
            )
            inputs = {
                name: args.output_dir / filename
                for name, filename in (
                    ("protocol", "protocol.json"),
                    ("history", "history.jsonl"),
                    ("fixtures", "fixtures.jsonl"),
                    ("quotes", "quotes.jsonl"),
                )
            }
            loaded, hashes = _load(inputs)
            result = run_study(**loaded)
            target = args.output_dir / "run"
        elif args.command == "study":
            inputs = {name: getattr(args, name) for name in ("protocol", "history", "fixtures", "quotes")}
            if args.baseline is not None:
                inputs["baseline"] = args.baseline
            loaded, hashes = _load(inputs)
            result = run_study(**loaded)
            target = args.output_dir
        else:
            inputs = {"quotes": args.quotes, "policy": args.policy}
            loaded, hashes = _load(inputs)
            result = {
                "scan.json": scan_quotes(
                    loaded["quotes"], as_of=timestamp(args.as_of), policy=price_policy(loaded["policy"])
                )
            }
            target = args.output_dir
        write_artifacts(
            target,
            inputs=inputs,
            artifacts=result,
            metadata={
                "status": "RESEARCH_ONLY",
                "input_hashes_used": hashes,
                "profitability_established": False,
                "real_capital_enabled": False,
            },
        )
        print(
            json.dumps(
                {
                    "status": "RESEARCH_ONLY",
                    "output_dir": str(target.resolve()),
                    "manifest_path": str(target.resolve() / "manifest.json"),
                    "profitability_established": False,
                },
                ensure_ascii=False,
            )
        )
        return 0
    except (ValueError, TypeError, KeyError, OSError) as exc:
        # Do not echo user data, transport payloads or arbitrary input fragments into terminal logs.
        print(f"Pesquisa recusada ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
