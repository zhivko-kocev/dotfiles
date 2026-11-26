---
name: "ci-cd-pipeline-builder"
description: "Generate CI/CD pipelines (GitHub Actions or GitLab CI) from detected repository signals. Language-agnostic and driven by profiles.json — adding a new stack means editing data, not code. Use when bootstrapping CI for a new repo, replacing a brittle copied pipeline, migrating between platforms, or auditing whether the pipeline matches the actual stack. Triggers on: 'add CI', 'github actions', 'gitlab ci', 'pipeline', 'workflow yaml'."
---

# CI/CD Pipeline Builder

**Tier:** POWERFUL  
**Category:** Engineering  
**Domain:** DevOps / Automation

## Overview

Use this skill to generate pragmatic CI/CD pipelines from detected project stack signals, not guesswork. It focuses on fast baseline generation, repeatable checks, and environment-aware deployment stages.

The detector and generator are **language-agnostic** — both iterate over `profiles.json`, which holds detection rules, package manager mappings, install/lint/test/build commands, and platform-specific setup blocks. Adding a new stack is a JSON edit, not a code change.

## Core Capabilities

- Detect language/runtime/tooling from repository files via profile rules
- Recommend CI stages (`lint`, `test`, `build`, `deploy`)
- Generate GitHub Actions or GitLab CI starter pipelines for any language with a profile
- Pick install commands from lockfile/manifest signals (e.g. pnpm vs yarn vs npm)
- Emit machine-readable detection output for automation
- Keep pipeline logic aligned with project lockfiles and build commands

## When to Use

- Bootstrapping CI for a new repository
- Replacing brittle copied pipeline files
- Migrating between GitHub Actions and GitLab CI
- Auditing whether pipeline steps match actual stack
- Creating a reproducible baseline before custom hardening

## Key Workflows

### 1. Detect Stack

```bash
python3 scripts/stack_detector.py --repo . --format text
python3 scripts/stack_detector.py --repo . --format json > detected-stack.json
```

Supports input via stdin or `--input` file for offline analysis payloads.

### 2. Generate Pipeline From Detection

```bash
python3 scripts/pipeline_generator.py \
  --input detected-stack.json \
  --platform github \
  --output .github/workflows/ci.yml \
  --format text
```

Or end-to-end from repo directly:

```bash
python3 scripts/pipeline_generator.py --repo . --platform gitlab --output .gitlab-ci.yml
```

### 3. Validate Before Merge

1. Confirm commands exist in project (`test`, `lint`, `build`).
2. Run generated pipeline locally where possible.
3. Ensure required secrets/env vars are documented.
4. Keep deploy jobs gated by protected branches/environments.

### 4. Add Deployment Stages Safely

- Start with CI-only (`lint/test/build`).
- Add staging deploy with explicit environment context.
- Add production deploy with manual gate/approval.
- Keep rollout/rollback commands explicit and auditable.

## Script Interfaces

- `python3 scripts/stack_detector.py --help`
  - Detects stack signals from repository files
  - Reads optional JSON input from stdin/`--input`
  - `--profiles PATH` to override `profiles.json` location
- `python3 scripts/pipeline_generator.py --help`
  - Generates GitHub/GitLab YAML from detection payload
  - Writes to stdout or `--output`
  - `--profiles PATH` to override `profiles.json` location
  - Falls back to running the detector when given `--repo` instead of stack input

## Extending Languages

`profiles.json` is the single source of truth. Each entry declares:

| Key | Purpose |
| --- | --- |
| `detect` | List of files (or globs like `*.csproj`) that signal the language is present |
| `pm_indicators` | Optional map of marker file → package manager (first match wins) |
| `default_pm` | Package manager when no indicator matches |
| `scripts_source` | Optional JSON manifest whose `scripts` field gates lint/test/build emission (used for Node) |
| `package_managers` | Per-PM commands (`install`, `lint`, `test`, `build`); `null` = skip |
| `github_setup` | YAML lines (without indent) injected before run steps in GitHub Actions |
| `gitlab_image` | Docker image used for GitLab CI jobs |

To add a stack (e.g. Rust): append a profile, declare `detect: ["Cargo.toml"]`, set the `cargo` package manager block, and provide setup/image. No script changes required.

## Common Pitfalls

1. Adding a stack to the repo without updating `profiles.json` (no jobs will be emitted)
2. Enabling deploy jobs before stable tests
3. Forgetting dependency cache keys
4. Running expensive matrix builds for every trivial branch
5. Missing branch protections around prod deploy jobs
6. Hardcoding secrets in YAML instead of CI secret stores

## Best Practices

1. Detect stack first, then generate pipeline.
2. Keep generated baseline under version control.
3. Add one optimization at a time (cache, matrix, split jobs).
4. Require green CI before deployment jobs.
5. Use protected environments for production credentials.
6. Regenerate pipeline when stack changes significantly.

## References

- [references/github-actions-templates.md](references/github-actions-templates.md)
- [references/gitlab-ci-templates.md](references/gitlab-ci-templates.md)
- [references/deployment-gates.md](references/deployment-gates.md)
- [README.md](README.md)

## Detection Heuristics

The stack detector prioritizes deterministic file signals over heuristics:

- Profiles in `profiles.json` declare which marker files imply each language
- `pm_indicators` in a profile determine package manager preference (e.g. `pnpm-lock.yaml` → pnpm)
- When a profile declares `scripts_source`, only scripts present in that manifest produce CI commands (avoids generating steps that call missing npm/yarn/pnpm scripts)
- Profiles without `scripts_source` always emit their default lint/test/build commands

## Generation Strategy

Start with a minimal, reliable pipeline:

1. Checkout and setup runtime
2. Install dependencies with cache strategy
3. Run lint, test, build in separate steps
4. Publish artifacts only after passing checks

Then layer advanced behavior (matrix builds, security scans, deploy gates).

## Platform Decision Notes

- GitHub Actions for tight GitHub ecosystem integration
- GitLab CI for integrated SCM + CI in self-hosted environments
- Keep one canonical pipeline source per repo to reduce drift

## Validation Checklist

1. Generated YAML parses successfully.
2. All referenced commands exist in the repo.
3. Cache strategy matches package manager.
4. Required secrets are documented, not embedded.
5. Branch/protected-environment rules match org policy.

## Scaling Guidance

- Split long jobs by stage when runtime exceeds 10 minutes.
- Introduce test matrix only when compatibility truly requires it.
- Separate deploy jobs from CI jobs to keep feedback fast.
- Track pipeline duration and flakiness as first-class metrics.
