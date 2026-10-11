#!/bin/zsh
# Double-click to start the MTG Cards web app; it opens in your browser. Close this window to stop it.
cd "$(dirname "$0")" && exec python3 server.py
