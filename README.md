# dotfiles

Personal dotfiles, linked into `$HOME` with [GNU stow](https://www.gnu.org/software/stow/).
They sit on top of [ultron](https://github.com/zhivko-kocev/ultron), which owns the desktop configs;
everything personal about this machine (browser, apps, monitor, disks) lives here instead of in ultron.

## What's inside

| Package | Files |
|---|---|
| `zsh` | `~/.zshenv`, `~/.zshrc`: history, completion, git prompt, mise, fzf, autosuggestions, syntax highlighting |
| `git` | `~/.config/git/config`: aliases and defaults; GitHub credentials through `gh` |
| `mise` | `~/.config/mise/config.toml`: personal tool versions (bun, dotnet, go, python) |
| `agents` | `~/.agents/AGENTS.md` (identity, rules, "This machine") and skills: `ci-cd-pipeline-builder`, `docker-development`, `find-skills` |
| `zed` | `~/.config/zed/settings.json`: Gruvbox Dark, JetBrains Mono |
| `ultron` | `~/.config/ultron/conf.d/10-personal.conf` (Chrome as `BROWSER`, the `projects` SSD in `MOUNTS`, LocalSend ports in `FIREWALL_ALLOW`), `~/.config/ultron/packages.txt` (Chrome, LibreOffice, qBittorrent, Stremio, LocalSend, the C/C++ toolchain), `~/.config/ultron/sway/10-personal.conf` (monitor mode, WhatsApp/Discord on workspace 7) |
| `apps` | `~/.local/share/applications/{whatsapp,discord,stremio}.desktop`: launcher entries for the Chrome app windows and Stremio |
| `bin` | `~/.local/bin/stremio`: starts `stremio-service` if needed, then the Stremio web app |
| `chrome` | `~/.config/chrome-flags.conf`: Wayland, and the `gnome-libsecret` password store the restored Chrome profile needs to keep its logins |

omp's own config (`~/.omp/agent/…`) is not here: `jocasta setup` owns it.

## How ultron uses this repo

ultron's `DOTFILES_REPO` setting (in `~/.config/ultron/ultron.conf`, or `ULTRON_DOTFILES` at bootstrap) names this repo.
`ultron install` clones it to `~/Projects/dotfiles` and runs `install.sh` early, before its own package and
desktop steps, so the `ultron` package's settings, extra packages and sway overrides are already in place.
Settings in `ultron.conf` win over `conf.d/10-personal.conf`. Nothing here depends on ultron having linked anything first.

## Install

```sh
git clone https://github.com/zhivko-kocev/dotfiles ~/Projects/dotfiles
~/Projects/dotfiles/install.sh
```

`install.sh` creates the shared parent folders, moves any file that would block a link to
`~/.dotfiles-backup/<UTC stamp>/`, runs `stow -R --no-folding -t ~ zsh git mise agents zed ultron apps bin chrome`,
enables the gitleaks pre-commit hook and makes zsh your login shell. Running it again is safe.

## Add a file

1. Put it inside a package folder at its path relative to `$HOME`
   (for example `zsh/.config/foo/bar` for `~/.config/foo/bar`), or make a new package folder.
2. If it is a new package, add its name to `packages` in `install.sh`.
3. Run `./install.sh` again.

## Secrets

Never commit secrets: this repo is public. Put token exports in `~/.config/zsh/secrets.zsh` (untracked, mode 600);
`~/.zshrc` sources it. The pre-commit hook runs `gitleaks` on staged changes and blocks the commit if it finds one.
