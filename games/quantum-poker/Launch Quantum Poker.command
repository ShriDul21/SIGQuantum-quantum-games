#!/bin/zsh
cd -- "${0:A:h}" || exit 1
python3 gui.py
result=$?
if (( result != 0 )); then
  printf '\nQuantum Poker could not start. Install dependencies with:\n  python3 -m pip install -r requirements-gui.txt\nUse Python with Tkinter and run from a graphical desktop.\n\nPress Return to close.\n'
  read -r
fi
exit "$result"
