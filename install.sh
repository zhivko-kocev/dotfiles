#!/usr/bin/env bash
# Link these dotfiles into $HOME with GNU stow.
set -euo pipefail

cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"

packages=(zsh git mise agents zed ultron apps bin chrome)

say() { printf '==> %s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

command -v stow >/dev/null || die "GNU stow is not installed. Install it with: sudo pacman -S stow"

# 1. Real parent folders first, so stow links files and not whole folders.
say "Creating the shared folders under ~/.config, ~/.local and ~/.agents"
mkdir -p "$HOME/.config/git" "$HOME/.config/mise" "$HOME/.agents/skills" \
  "$HOME/.config/ultron/conf.d" "$HOME/.config/ultron/sway" \
  "$HOME/.local/bin" "$HOME/.local/share/applications"

# 2. Move files that would block stow out of the way.
say "Checking for files that would conflict"
dry=$(stow -n -v -R --no-folding -t "$HOME" "${packages[@]}" 2>&1 || true)
conflicts=()
while IFS= read -r line; do
  path=""
  case "$line" in
    *"existing target is neither a link nor a directory: "*)
      path=${line##*existing target is neither a link nor a directory: }
      ;;
    *"cannot stow "*" over existing target "*" since "*)
      path=${line##* over existing target }
      path=${path%% since *}
      ;;
    *"existing target is not owned by stow: "*)
      path=${line##*existing target is not owned by stow: }
      ;;
  esac
  [[ -n $path ]] && conflicts+=("$path")
done <<<"$dry"

if ((${#conflicts[@]})); then
  backup="$HOME/.dotfiles-backup/$(date -u +%Y%m%dT%H%M%SZ)"
  for rel in "${conflicts[@]}"; do
    [[ -e "$HOME/$rel" || -L "$HOME/$rel" ]] || continue
    mkdir -p "$backup/$(dirname "$rel")"
    mv "$HOME/$rel" "$backup/$rel"
    say "Moved ~/$rel to $backup/$rel"
  done
fi

# 3. Link.
say "Linking packages: ${packages[*]}"
stow -R --no-folding -t "$HOME" "${packages[@]}" || die "stow failed. Read the messages above, fix the listed paths, then run ./install.sh again"

# 4. Secret scan before every commit.
if git rev-parse --git-dir >/dev/null 2>&1; then
  say "Enabling the gitleaks pre-commit hook"
  git config core.hooksPath .githooks
fi

# 5. zsh as the login shell.
zsh_path=/usr/bin/zsh
current=$(getent passwd "$USER" | cut -d: -f7)
if [[ $current != "$zsh_path" ]]; then
  [[ -x $zsh_path ]] || die "zsh is not installed. Install it with: sudo pacman -S zsh"
  say "Changing your login shell to zsh (sudo may ask for your password)"
  # sudo, not plain chsh: chsh asks for the password on the terminal itself, which hangs when run from a script.
  sudo chsh -s "$zsh_path" "$USER"
fi

say "Done. Open a new terminal to use the new shell settings."
