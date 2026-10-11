# MTG Cards

This folder is a local app, not part of the GitHub Pages site: it needs `server.py` running on your Mac.

A small local web app for the `mtg-cards` Claude Code agent: ask about any Magic card, printing, set or artist, and get answers with card images.

## Start it

Double-click **Start MTG Cards.command**, or run:

```bash
python3 server.py
```

It opens http://127.0.0.1:8790 in your browser. Close the Terminal window (or press Ctrl+C) to stop it.

## How it works

- `server.py` serves `app.html` and runs each question through the real agent with the Claude Code CLI (`claude -p --agent mtg-cards`), using your Claude Code sign-in. Follow-up questions continue the same agent session; **New chat** starts over.
- The agent reads the saved card data in `~/.claude/agents/mtg-judge-data/` (refresh it with `python3 build/export_agent_data.py` from the repo root) and may check Scryfall or Commander Spellbook. It can only run read-only lookups (grep, awk, cut, head, sort, wc, curl) and read files.
- The server only listens on 127.0.0.1 and refuses requests from other websites.
- The CLI is found on PATH, or inside the Claude desktop app. Set `MTG_CLAUDE=/path/to/claude` to choose one.
