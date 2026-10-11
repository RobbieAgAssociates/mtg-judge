"""MTG Cards: a small local web app for the mtg-cards Claude Code agent.

Run it, then open http://127.0.0.1:8790 (the script opens it for you):
    python3 server.py            # or double-click "Start MTG Cards.command"
    python3 server.py --port 8791 --no-browser

Each time the page is opened or reloaded, the server checks Scryfall in the background and, when Scryfall has newer
card data than the saved copy, refreshes it (cards, rulings and printings), rebuilds the site files and re-exports the
agents' data. Turn that off with --no-refresh.

Each question runs the real agent through the Claude Code CLI (`claude -p --agent mtg-cards`) on this Mac,
using your Claude Code sign-in. Follow-up questions resume the same agent session. The server listens on
127.0.0.1 only and refuses requests from other websites.
"""
import argparse, glob, json, os, re, shutil, subprocess, sys, threading, time, urllib.request, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.expanduser("~/.claude/agents/mtg-judge-data")          # saved data shared with mtg-judge
SITE = os.path.dirname(HERE)                                           # the website repo, for the mana symbol images
SESSION_RX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
TIMEOUT = 300  # seconds per answer

# Rules for running inside the app: these keep every lookup within what the allowed tools below permit.
APP_PROMPT = (
    "You are answering inside the MTG Cards web app. The working directory is the saved data folder, so use bare file names "
    "(cards.tsv, prints.tsv, cardinfo.tsv, rulings.tsv, combos.tsv, precons.tsv, sets.tsv, info.txt). Run one simple command per Bash call: "
    "no cd, no shell variables, no $'...' quoting, no python. Match names with awk -F'\\t' '$1==\"Card Name\"' file, or grep -F. "
    "Pipes into cut, head, sort and wc are fine. Use curl only for Scryfall or Commander Spellbook when the saved data lacks something. "
    "Never run open; the page shows your Markdown images and links. Show card images as Markdown images and link card names to the Card Index. "
    "If a question is about rules interactions or deck analysis, answer briefly and suggest asking the mtg-judge agent."
)
ALLOWED = ["Read", "Grep", "Bash(grep:*)", "Bash(awk:*)", "Bash(cut:*)", "Bash(head:*)", "Bash(sort:*)", "Bash(wc:*)", "Bash(curl:*)"]


def find_claude():
    """The Claude Code CLI: $MTG_CLAUDE, `claude` on PATH, or the newest copy bundled with the Claude desktop app."""
    if os.environ.get("MTG_CLAUDE"):
        return os.environ["MTG_CLAUDE"]
    if shutil.which("claude"):
        return shutil.which("claude")
    found = glob.glob(os.path.expanduser("~/Library/Application Support/Claude/claude-code/*/*/claude.app/Contents/MacOS/claude"))
    version = lambda p: [int(x) for x in re.findall(r"\d+", p.split("/claude-code/")[1].split("/")[0])]
    return max(found, key=version) if found else None


class Refresher:
    """Refresh the saved card data when Scryfall has published newer data. One refresh at a time; checks are rate-limited."""
    CHECK_EVERY = 120   # seconds between Scryfall checks, so reloading the page doesn't hammer it
    STAMP = os.path.join(DATA, "scryfall_stamp.json")

    def __init__(self, enabled):
        self.enabled = enabled
        self.lock = threading.Lock()
        self.last_check = 0.0
        self.state = {"status": "off" if not enabled else "idle", "message": "" if enabled else "Automatic data refresh is off."}

    def set(self, status, message):
        self.state = {"status": status, "message": message, "at": time.strftime("%H:%M")}

    def trigger(self):
        if not self.enabled or self.state["status"] in ("checking", "updating") or time.time() - self.last_check < self.CHECK_EVERY:
            return
        self.last_check = time.time()
        threading.Thread(target=self.run, daemon=True).start()

    def scryfall_updated(self):
        req = urllib.request.Request("https://api.scryfall.com/bulk-data", headers={"User-Agent": "mtg-cards-app/1.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)["data"]
        return max(b["updated_at"][:19] for b in data if b["type"] in ("oracle_cards", "default_cards", "rulings"))

    def saved_stamp(self):
        try:
            return json.load(open(self.STAMP))["scryfall_updated"]
        except (OSError, ValueError, KeyError):
            pass
        # no stamp yet: treat data saved on a given day as covering Scryfall's files from that day
        m = re.search(r"Data saved (\d{4}-\d{2}-\d{2})", open(os.path.join(DATA, "info.txt")).read()) if os.path.exists(os.path.join(DATA, "info.txt")) else None
        return m.group(1) + "T23:59:59" if m else ""

    def write_stamp(self, stamp):
        with open(self.STAMP + ".tmp", "w") as f:
            json.dump({"scryfall_updated": stamp, "refreshed": time.strftime("%Y-%m-%d %H:%M")}, f)
        os.replace(self.STAMP + ".tmp", self.STAMP)

    def run(self):
        if not self.lock.acquire(blocking=False):
            return
        try:
            self.set("checking", "Checking Scryfall for new card data")
            latest, saved = self.scryfall_updated(), self.saved_stamp()
            if saved and latest <= saved:
                if not os.path.exists(self.STAMP):
                    self.write_stamp(saved)
                self.set("current", f"Card data is up to date (Scryfall {latest[:10]}).")
                return
            self.set("updating", f"Scryfall has new card data ({latest[:10]}). Updating; this takes a few minutes, and answers use the current data until it's done.")
            steps = [[sys.executable, os.path.join(SITE, "build", "refresh_data.py"), "cards", "rulings", "prints"],
                     [sys.executable, os.path.join(SITE, "build", "make_site.py")],
                     [sys.executable, os.path.join(SITE, "build", "export_agent_data.py"), DATA]]
            for cmd in steps:
                r = subprocess.run(cmd, cwd=SITE, capture_output=True, text=True, timeout=1800)
                out = (r.stdout + r.stderr).strip().splitlines()
                if r.returncode != 0 or any("FAILED" in line for line in out):
                    raise RuntimeError(next((l for l in out if "FAILED" in l), out[-1] if out else f"exit {r.returncode}")[:200])
            self.write_stamp(latest)
            self.set("updated", f"Card data updated from Scryfall ({latest[:10]}).")
        except Exception as e:
            self.set("error", f"Couldn't refresh the card data: {e}. The saved data is still in use; it will try again next time you open the app.")
            self.last_check = 0.0
        finally:
            self.lock.release()


def describe(tool, inp):
    """A short, friendly progress line for one of the agent's tool calls."""
    if tool == "Bash":
        cmd = inp.get("command", "")
        if "curl" in cmd:
            return "Checking Commander Spellbook" if "spellbook" in cmd else "Checking Scryfall"
        names = re.findall(r"\b(cards|cardinfo|prints|rulings|combos|precons|sets)\.tsv", cmd)
        what = {"cards": "card text", "cardinfo": "formats, prices and tags", "prints": "printings", "rulings": "rulings",
                "combos": "combos", "precons": "precons", "sets": "sets"}
        return "Reading " + ", ".join(dict.fromkeys(what[n] for n in names)) if names else (inp.get("description") or "Searching the saved data")
    if tool in ("Read", "Grep"):
        return "Reading the saved data"
    if tool == "WebFetch":
        return "Reading a web page"
    if tool == "WebSearch":
        return "Searching the web"
    return "Working"


class Handler(BaseHTTPRequestHandler):
    server_version = "MTGCards/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("  " + (fmt % args) + "\n")

    def same_origin(self):
        host = self.headers.get("Host", "")
        ok_hosts = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        origin = self.headers.get("Origin")
        return host in ok_hosts and (origin is None or origin.split("://", 1)[-1] in ok_hosts)

    def send_file(self, path, ctype):
        try:
            body = open(path, "rb").read()
        except OSError:
            return self.send_error(404)
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.same_origin():
            return self.send_error(403)
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self.server.refresher.trigger()   # every open or reload checks for new card data
            return self.send_file(os.path.join(HERE, "app.html"), "text/html; charset=utf-8")
        if path == "/symbols.json":
            return self.send_file(os.path.join(SITE, "build", "data", "symbols.json"), "application/json")
        m = re.fullmatch(r"/img/sym/([A-Za-z0-9_\-]+\.svg)", path)
        if m:
            return self.send_file(os.path.join(SITE, "img", "sym", m.group(1)), "image/svg+xml")
        if path == "/api/refresh":
            return self.json(self.server.refresher.state)
        if path == "/api/info":
            info = open(os.path.join(DATA, "info.txt")).read() if os.path.exists(os.path.join(DATA, "info.txt")) else ""
            return self.json({"claude": bool(self.server.claude), "data": info.strip()})
        self.send_error(404)

    def json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        # Same origin and a JSON body only: another website can't make a browser send this without a CORS preflight, which we never answer.
        if self.path != "/api/ask" or not self.same_origin() or not self.headers.get("Content-Type", "").startswith("application/json"):
            return self.send_error(403)
        try:
            req = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 20000)))
            question = str(req.get("question", "")).strip()[:4000]
            session = str(req.get("session") or "")
        except (ValueError, TypeError):
            return self.send_error(400)
        if not question:
            return self.json({"error": "Type a question first."}, 400)
        if not self.server.claude:
            return self.json({"error": "Couldn't find the Claude Code CLI. Install Claude Code, or set MTG_CLAUDE to its path."}, 500)
        cmd = [self.server.claude, "-p", question, "--agent", "mtg-cards", "--output-format", "stream-json", "--verbose",
               "--add-dir", DATA, "--append-system-prompt", APP_PROMPT, "--max-turns", "25", "--allowedTools", *ALLOWED]
        if SESSION_RX.match(session):
            cmd[3:3] = ["--resume", session]

        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        def emit(obj):
            self.wfile.write((json.dumps(obj) + "\n").encode())
            self.wfile.flush()

        proc = subprocess.Popen(cmd, cwd=DATA, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        timer = threading.Timer(TIMEOUT, proc.kill)
        timer.start()
        got_result = False
        try:
            emit({"type": "status", "text": "Thinking"})
            for line in proc.stdout:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                t = e.get("type")
                if t == "assistant":
                    for b in e.get("message", {}).get("content", []):
                        if b.get("type") == "tool_use":
                            emit({"type": "status", "text": describe(b.get("name"), b.get("input") or {})})
                        elif b.get("type") == "text" and b.get("text", "").strip():
                            emit({"type": "text", "text": b["text"]})
                elif t == "result":
                    got_result = True
                    if e.get("is_error") or e.get("subtype") != "success":
                        emit({"type": "error", "text": "The agent stopped early (" + str(e.get("subtype")) + "). Try asking a narrower question.",
                              "session": e.get("session_id")})
                    else:
                        emit({"type": "done", "answer": e.get("result", ""), "session": e.get("session_id"),
                              "seconds": round((e.get("duration_ms") or 0) / 1000), "cost": e.get("total_cost_usd")})
            proc.wait()
            if not got_result:
                err = (proc.stderr.read() or "").strip().splitlines()
                emit({"type": "error", "text": "The agent didn't finish" + (": " + err[-1][:300] if err else (" (timed out)" if proc.returncode else ".")) })
        except (BrokenPipeError, ConnectionResetError):
            pass  # the page was closed or the question was cancelled
        finally:
            timer.cancel()
            if proc.poll() is None:
                proc.kill()


def main():
    ap = argparse.ArgumentParser(description="MTG Cards web app")
    ap.add_argument("--port", type=int, default=8790)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--no-refresh", action="store_true", help="don't check Scryfall for new card data when the page opens")
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    srv.claude = find_claude()
    srv.refresher = Refresher(not args.no_refresh)
    url = f"http://127.0.0.1:{args.port}/"
    sys.stdout.reconfigure(line_buffering=True)
    print(f"MTG Cards is running at {url}  (Ctrl+C to stop)")
    print("Claude Code CLI:", srv.claude or "NOT FOUND - set MTG_CLAUDE to its path")
    if not os.path.exists(os.path.join(DATA, "prints.tsv")):
        print("Saved card data is missing. In the website folder run: python3 build/export_agent_data.py")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
