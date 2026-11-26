#!/usr/bin/env python3
"""Generate CI pipeline YAML from detected stack data.

The generator reads profiles.json (single source of truth) and the per-language
entries produced by stack_detector. Every job is built by iterating profile
setup blocks and entry commands — no hardcoded language branches.

Input sources:
- --input stack report JSON file
- stdin stack report JSON
- --repo path (auto-detect via stack_detector)
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack_detector import (  # noqa: E402
    PROFILES_PATH,
    CLIError,
    detect,
    load_profiles,
)


@dataclass
class PipelineSummary:
    platform: str
    output: str
    stages: List[str]
    languages: List[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate CI/CD pipeline YAML from detected stack.")
    parser.add_argument("--input", help="Stack report JSON file. If omitted, can read stdin JSON.")
    parser.add_argument("--repo", help="Repository path for auto-detection fallback.")
    parser.add_argument("--platform", choices=["github", "gitlab"], required=True, help="Target CI platform.")
    parser.add_argument("--profiles", default=str(PROFILES_PATH), help="Path to profiles.json.")
    parser.add_argument("--output", help="Write YAML to this file; otherwise print to stdout.")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Summary output format.")
    return parser.parse_args()


def load_json_input(input_path: Optional[str]) -> Optional[Dict[str, Any]]:
    if input_path:
        try:
            return json.loads(Path(input_path).read_text(encoding="utf-8"))
        except Exception as exc:
            raise CLIError(f"Failed reading --input: {exc}") from exc

    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                raise CLIError(f"Invalid JSON from stdin: {exc}") from exc

    return None


def stage_command(entry: Dict[str, Any], pm_template: Dict[str, Any], stage: str) -> Optional[str]:
    """Return the command for a stage, a placeholder, or None to skip.

    - Real command if the entry resolved one (script present, etc.)
    - `echo` placeholder if the profile *has* a command for this stage but the
      detector gated it out (e.g. node project with no `lint` script). This
      keeps the generated job a valid skeleton the user can fill in later.
    - None if the profile declares no command for this stage at all (e.g.
      python build) — emitting a placeholder there would be noise.
    """
    cmd = entry.get(f"{stage}_command")
    if cmd:
        return cmd
    if pm_template.get(stage) is not None:
        return f"echo 'No {stage} command configured'"
    return None


def github_yaml(stack: Dict[str, Any], profiles: Dict[str, dict]) -> str:
    lines: List[str] = [
        "name: CI",
        "on:",
        "  push:",
        "    branches: [main, develop]",
        "  pull_request:",
        "    branches: [main, develop]",
        "",
        "jobs:",
    ]

    for entry in stack.get("entries") or []:
        profile = profiles.get(entry["language"])
        if not profile:
            continue
        pm_template = profile["package_managers"].get(entry["package_manager"], {})

        steps: List[str] = []
        if entry.get("install_command"):
            steps.append(f"      - run: {entry['install_command']}")
        for stage in ("lint", "test", "build"):
            cmd = stage_command(entry, pm_template, stage)
            if cmd:
                steps.append(f"      - run: {cmd}")
        if not steps:
            continue

        lines.append(f"  {entry['language']}-ci:")
        lines.append("    runs-on: ubuntu-latest")
        lines.append("    steps:")
        for setup in profile.get("github_setup", []):
            lines.append(f"      {setup}")
        lines.extend(steps)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def gitlab_yaml(stack: Dict[str, Any], profiles: Dict[str, dict]) -> str:
    lines: List[str] = [
        "stages:",
        "  - lint",
        "  - test",
        "  - build",
        "",
    ]

    for entry in stack.get("entries") or []:
        profile = profiles.get(entry["language"])
        if not profile:
            continue
        pm_template = profile["package_managers"].get(entry["package_manager"], {})
        image = profile.get("gitlab_image", "alpine:latest")
        install = entry.get("install_command")

        for stage in ("lint", "test", "build"):
            cmd = stage_command(entry, pm_template, stage)
            if not cmd:
                continue
            lines.append(f"{entry['language']}_{stage}:")
            lines.append(f"  image: {image}")
            lines.append(f"  stage: {stage}")
            lines.append("  script:")
            if install:
                lines.append(f"    - {install}")
            lines.append(f"    - {cmd}")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    profiles = load_profiles(Path(args.profiles))
    stack = load_json_input(args.input)

    if stack is None:
        if not args.repo:
            raise CLIError("Provide stack input via --input/stdin or set --repo for auto-detection.")
        repo = Path(args.repo).resolve()
        if not repo.exists() or not repo.is_dir():
            raise CLIError(f"Invalid repo path: {repo}")
        stack = asdict(detect(repo, profiles))

    yaml_content = github_yaml(stack, profiles) if args.platform == "github" else gitlab_yaml(stack, profiles)

    output_path = args.output or "stdout"
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(yaml_content, encoding="utf-8")
    else:
        print(yaml_content, end="")

    summary = PipelineSummary(
        platform=args.platform,
        output=output_path,
        stages=["lint", "test", "build"],
        languages=stack.get("languages", []),
    )

    # Keep the YAML stream clean: when YAML goes to stdout, summary goes to
    # stderr so it can't pollute redirected pipeline files.
    summary_stream = sys.stdout if args.output else sys.stderr
    if args.format == "json":
        print(json.dumps(asdict(summary), indent=2), file=summary_stream)
    else:
        print(
            "Pipeline generated\n"
            f"- platform: {summary.platform}\n"
            f"- output: {summary.output}\n"
            f"- stages: {', '.join(summary.stages)}\n"
            f"- languages: {', '.join(summary.languages) or 'none'}",
            file=summary_stream,
        )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CLIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
