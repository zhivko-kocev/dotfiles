#!/usr/bin/env python3
"""Detect project stack/tooling signals for CI/CD pipeline generation.

Stack profiles live in profiles.json. The detector iterates over those
profiles instead of hardcoding language-specific branches.

Input sources:
- repository scan via --repo
- JSON via --input file
- JSON via stdin
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


PROFILES_PATH = Path(__file__).resolve().parent.parent / "profiles.json"


class CLIError(Exception):
    """Raised for expected CLI failures."""


@dataclass
class StackEntry:
    language: str
    package_manager: str
    install_command: Optional[str]
    lint_command: Optional[str]
    test_command: Optional[str]
    build_command: Optional[str]


@dataclass
class StackReport:
    repo: str
    languages: List[str]
    package_managers: List[str]
    ci_targets: List[str]
    test_commands: List[str]
    build_commands: List[str]
    lint_commands: List[str]
    signals: Dict[str, bool]
    entries: List[Dict] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect stack/tooling from a repository.")
    parser.add_argument("--input", help="JSON input file (precomputed signal payload).")
    parser.add_argument("--repo", default=".", help="Repository path to scan.")
    parser.add_argument("--profiles", default=str(PROFILES_PATH), help="Path to profiles.json.")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")
    return parser.parse_args()


def load_profiles(path: Path) -> Dict[str, dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CLIError(f"Failed reading profiles {path}: {exc}") from exc


def load_payload(input_path: Optional[str]) -> Optional[dict]:
    if input_path:
        try:
            return json.loads(Path(input_path).read_text(encoding="utf-8"))
        except Exception as exc:
            raise CLIError(f"Failed reading --input file: {exc}") from exc

    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                raise CLIError(f"Invalid JSON from stdin: {exc}") from exc

    return None


def matches_any(repo: Path, patterns: List[str]) -> bool:
    for pattern in patterns:
        if any(ch in pattern for ch in "*?["):
            if any(repo.glob(pattern)):
                return True
        elif (repo / pattern).exists():
            return True
    return False


def read_scripts(repo: Path, source: str) -> Dict[str, str]:
    path = repo / source
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    scripts = data.get("scripts", {})
    return scripts if isinstance(scripts, dict) else {}


def select_pm(repo: Path, profile: dict) -> str:
    for marker, pm in (profile.get("pm_indicators") or {}).items():
        if (repo / marker).exists():
            return pm
    return profile["default_pm"]


def detect_entry(repo: Path, language: str, profile: dict) -> Optional[StackEntry]:
    if not matches_any(repo, profile.get("detect", [])):
        return None

    pm = select_pm(repo, profile)
    pm_commands = profile["package_managers"].get(pm)
    if pm_commands is None:
        raise CLIError(f"Profile '{language}' missing package_managers entry for '{pm}'.")

    scripts_source = profile.get("scripts_source")
    available = read_scripts(repo, scripts_source) if scripts_source else None

    def pick(key: str) -> Optional[str]:
        cmd = pm_commands.get(key)
        if not cmd:
            return None
        # If a scripts source is declared, only emit the command when the
        # corresponding script is present — avoid generating CI steps that
        # would call missing npm/yarn/pnpm scripts.
        if available is not None and key not in available:
            return None
        return cmd

    return StackEntry(
        language=language,
        package_manager=pm,
        install_command=pm_commands.get("install"),
        lint_command=pick("lint"),
        test_command=pick("test"),
        build_command=pick("build"),
    )


def detect(repo: Path, profiles: Dict[str, dict]) -> StackReport:
    entries: List[StackEntry] = []
    signals: Dict[str, bool] = {}

    for language, profile in profiles.items():
        signals[language] = matches_any(repo, profile.get("detect", []))
        entry = detect_entry(repo, language, profile)
        if entry is not None:
            entries.append(entry)

    signals["dockerfile"] = (repo / "Dockerfile").exists()
    signals["helm"] = (repo / "helm").exists() or (repo / "charts").exists()
    signals["k8s"] = (repo / "k8s").exists() or (repo / "kubernetes").exists()

    lint = sorted({e.lint_command for e in entries if e.lint_command})
    test = sorted({e.test_command for e in entries if e.test_command})
    build = sorted({e.build_command for e in entries if e.build_command})

    return StackReport(
        repo=str(repo.resolve()),
        languages=sorted({e.language for e in entries}),
        package_managers=sorted({e.package_manager for e in entries}),
        ci_targets=["github", "gitlab"],
        test_commands=test,
        build_commands=build,
        lint_commands=lint,
        signals=signals,
        entries=[asdict(e) for e in entries],
    )


def format_text(report: StackReport) -> str:
    lines = [
        "Detected stack",
        f"- repo: {report.repo}",
        f"- languages: {', '.join(report.languages) or 'none'}",
        f"- package managers: {', '.join(report.package_managers) or 'none'}",
    ]
    for entry in report.entries:
        lines.append(f"- {entry['language']} ({entry['package_manager']}):")
        for key in ("install_command", "lint_command", "test_command", "build_command"):
            if entry[key]:
                lines.append(f"    {key.replace('_command', '')}: {entry[key]}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    profiles = load_profiles(Path(args.profiles))
    payload = load_payload(args.input)

    if payload:
        try:
            report = StackReport(**payload)
        except TypeError as exc:
            raise CLIError(f"Invalid input payload for StackReport: {exc}") from exc
    else:
        repo = Path(args.repo).resolve()
        if not repo.exists() or not repo.is_dir():
            raise CLIError(f"Invalid repo path: {repo}")
        report = detect(repo, profiles)

    if args.format == "json":
        print(json.dumps(asdict(report), indent=2))
    else:
        print(format_text(report))

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CLIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
