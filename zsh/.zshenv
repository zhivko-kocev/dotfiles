typeset -U path
path=(~/.local/bin $path)

if [[ -n $SSH_CONNECTION ]]; then
  export EDITOR="nano" VISUAL="nano"
else
  export EDITOR="zeditor --wait" VISUAL="zeditor --wait"
fi
