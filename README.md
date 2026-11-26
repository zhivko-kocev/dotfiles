# dotfiles

Personal dotfiles, linked into `$HOME` with [GNU stow](https://www.gnu.org/software/stow/).
They sit on top of [ultron](https://github.com/zhivko-kocev/ultron), which owns the desktop configs.

## What's inside

| Package | Files |
|---|---|
| `zsh` | `~/.zshenv`, `~/.zshrc`: history, completion, git prompt, mise, fzf, autosuggestions, syntax highlighting |
| `git` | `~/.config/git/config`: aliases and defaults; GitHub credentials through `gh` |
| `mise` | `~/.config/mise/config.toml`: personal tool versions (bun, dotnet, go, python) |
| `agents` | `~/.agents/AGENTS.md` (identity, rules, "This machine") and skills: `ci-cd-pipeline-builder`, `docker-development`, `find-skills` |
| `zed` | `~/.config/zed/settings.json`: Gruvbox Dark, JetBrains Mono |

omp's own config (`~/.omp/agent/…`) is not here: `jocasta setup` owns it.

## Install

```sh
git clone https://github.com/zhivko-kocev/dotfiles ~/Projects/dotfiles
~/Projects/dotfiles/install.sh
```

`install.sh` creates the shared parent folders, moves any file that would block a link to
`~/.dotfiles-backup/<UTC stamp>/`, runs `stow -R -t ~ zsh git mise agents zed`, enables the
gitleaks pre-commit hook and makes zsh your login shell. Running it again is safe.

## Add a file

1. Put it inside a package folder at its path relative to `$HOME`
   (for example `zsh/.config/foo/bar` for `~/.config/foo/bar`), or make a new package folder.
2. If it is a new package, add its name to `packages` in `install.sh`.
3. Run `./install.sh` again.

## Secrets

Never commit secrets. The pre-commit hook runs `gitleaks` on staged changes and blocks the commit if it finds one.
