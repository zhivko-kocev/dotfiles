# History
HISTFILE=~/.zsh_history
HISTSIZE=50000
SAVEHIST=50000
setopt share_history hist_ignore_dups hist_ignore_space extended_history auto_cd interactive_comments

# Emacs-style line editing
bindkey -e

# Completion: case-insensitive, with a menu
autoload -Uz compinit
mkdir -p ~/.cache
compinit -d ~/.cache/zcompdump
zstyle ':completion:*' menu select
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}'

# Prompt: user@host ~/path (branch) %
autoload -Uz vcs_info
zstyle ':vcs_info:git:*' formats ' (%b)'
zstyle ':vcs_info:git:*' actionformats ' (%b|%a)'
precmd() { vcs_info }
setopt prompt_subst
PROMPT='%F{green}%n@%m%f %F{blue}%~%f${vcs_info_msg_0_} %# '

# Project tools without touching the repo (ultron): inside a git repository whose folder is NAME (worktrees
# count as their main repository), ~/.config/mise/config.NAME.toml is loaded too, through MISE_ENV.
# `ultron dev project` creates that file. This must come before `mise activate`.
typeset -g _ultron_mise_env0=${MISE_ENV-}
_ultron_mise_env() {
  local common name
  common=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || common=
  name=${${common:h}:t}
  if [[ -n $common && -f ~/.config/mise/config.$name.toml ]]; then
    if [[ ,$_ultron_mise_env0, == *,$name,* ]]; then
      export MISE_ENV=$_ultron_mise_env0
    else
      export MISE_ENV=${_ultron_mise_env0:+$_ultron_mise_env0,}$name
    fi
  elif [[ -n $_ultron_mise_env0 ]]; then
    export MISE_ENV=$_ultron_mise_env0
  else
    unset MISE_ENV
  fi
}
chpwd_functions+=(_ultron_mise_env)
_ultron_mise_env

# Tools
if (( $+commands[mise] )); then
  eval "$(mise activate zsh)"
fi
if (( $+commands[fzf] )); then
  source <(fzf --zsh)
fi

# Aliases
alias ls='ls --color=auto'
alias ll='ls -lah --color=auto'
alias grep='grep --color=auto'

# Tokens go in this untracked file (mode 600), never in this repo: it is public.
[[ -r ~/.config/zsh/secrets.zsh ]] && source ~/.config/zsh/secrets.zsh

# Plugins (syntax highlighting must be last)
if [[ -r /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh ]]; then
  source /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh
fi
if [[ -r /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]]; then
  source /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
fi
