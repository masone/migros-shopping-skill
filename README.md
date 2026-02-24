# migros-shopping/SKILL.md

TODO: 
- describe separate user

An AI agent skill that automates shopping on [migros.ch](https://www.migros.ch) — search for products, build a cart, and generate a shareable list link. Works with **Claude Code** and **OpenClaw**.

Uses [`@playwright/cli`](https://www.npmjs.com/package/@playwright/cli) for browser automation and [Camoufox](https://github.com/daijro/camoufox) — an anti-detect Firefox build — to bypass Migros bot protection.

---

## How it works

```
Claude / Agent
     │
     │  playwright-cli commands
     ▼
playwright-cli ──(WebSocket)──► Camoufox (local Python process)
                  ws://localhost:9222    └── Firefox + fingerprint spoofing
                                              └── migros.ch
```

`playwright-cli` is a zero-overhead browser CLI: each command returns only the result (~50–200 bytes). The Migros scripts in `./scripts/` are injected via `run-code` — no Playwright test runner needed.

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- A Migros account with online shopping enabled

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
python -m camoufox fetch
npm install
```

`python -m camoufox fetch` downloads the Firefox binary once (~200 MB, cached).

### 2. Configure your shell

Add to `~/.zshrc` or `~/.bashrc`:

```bash
export MIGROS_SKILL_DIR="/absolute/path/to/migros-shopping-skill"
export MIGROS_USER="your@email.com"
export MIGROS_PASS="yourpassword"
export PATH="$PATH:$MIGROS_SKILL_DIR/node_modules/.bin"
```

### 3. Start the browser

```bash
python3 "$MIGROS_SKILL_DIR/camoufox/launch_server.py" &
```

Starts Camoufox in the background on `ws://localhost:9222/browser`.

### 4. Verify

```bash
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" open https://www.migros.ch/de
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" snapshot
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" close
```

---

## Configuration

### `cli.config.json`

```json
{
  "browser": {
    "browserName": "firefox",
    "remoteEndpoint": "ws://localhost:9222/browser",
    "contextOptions": {
      "viewport": { "width": 1920, "height": 1080 },
      "locale": "de-CH",
      "timezoneId": "Europe/Zurich"
    }
  }
}
```

### Environment variables

| Variable | Description |
|---|---|
| `MIGROS_SKILL_DIR` | Absolute path to this directory |
| `MIGROS_USER` | Migros account email |
| `MIGROS_PASS` | Migros account password |

---

## Usage with Claude Code

1. Add the shell exports above to your profile and reload.
2. Start the browser server.
3. Ask Claude:

> "Fill my Migros cart with: 2x whole milk, pasta, tomatoes, bread, and butter."

Claude follows the workflow in `SKILL.md` automatically.

**`CLAUDE.md` snippet:**

```markdown
## Migros Shopping

See SKILL.md in $MIGROS_SKILL_DIR for the full workflow.
```

---

## Usage with OpenClaw

Drop this directory into your OpenClaw skills directory — `SKILL.md` is discovered automatically.

In `openclaw.json`:
```json
{
  "skills": {
    "extraDirs": ["/path/to/your/skills"]
  }
}
```

---

## Workflow overview

1. **Login** — authenticates, creates a new shopping list, returns a share URL
2. **Add products** — by product ID (fastest) or text search + pick
3. **Validate cart** — returns item count and total price
4. **Close** — releases the browser session

Search queries must be in **German** (e.g. "Vollmilch", "Teigwaren", "Butter").

---

## Scripts

| Script | Purpose | Placeholders |
|---|---|---|
| `migros-login.js` | Login + create new list + get share URL | `__USER__`, `__PASS__` |
| `migros-search.js` | Search products by query | `__QUERY__` |
| `migros-pick.js` | Add product by search result index | `__INDEX__` |
| `migros-add.js` | Add product by ID or query (first result) | `__QUERY__` |
| `migros-offers.js` | Fetch current promotions | — |
| `migros-cart.js` | Get cart item count and total | — |

Placeholders are replaced at runtime via `sed` — no script files are modified.

---

## Project structure

```
migros-shopping-skill/
├── SKILL.md              # Skill definition for Claude Code / OpenClaw
├── README.md             # This file
├── requirements.txt      # Python deps (camoufox, orjson)
├── package.json          # @playwright/cli dependency
├── cli.config.json       # Browser config (endpoint, locale, viewport)
├── camoufox/
│   ├── launch_server.py  # Camoufox WebSocket server on port 9222
│   ├── Dockerfile        # Alternative: Docker image (for Linux servers)
│   └── entrypoint.sh     # Docker entrypoint (Xvfb + Python server)
└── scripts/
    ├── migros-login.js
    ├── migros-search.js
    ├── migros-pick.js
    ├── migros-add.js
    ├── migros-offers.js
    └── migros-cart.js
```

---

## Troubleshooting

**`connect ECONNREFUSED localhost:9222`**
Camoufox is not running. Start it:
```bash
python3 "$MIGROS_SKILL_DIR/camoufox/launch_server.py" &
```

**`version mismatch: server v1.X / client v1.Y`**
Camoufox and `@playwright/cli` bundle different Playwright driver versions. Fix by upgrading camoufox's bundled driver to match:
```bash
PW_DRIVER=$(python3 -c "from camoufox.server import get_nodejs; from pathlib import Path; print(Path(get_nodejs()).parent)")
curl -sL https://registry.npmjs.org/playwright-core/-/playwright-core-1.59.0-alpha-1771104257000.tgz \
  | tar -xz -C /tmp
rm -rf "$PW_DRIVER/package" && mv /tmp/package "$PW_DRIVER/package"
```

**Bot challenge / CAPTCHA**
Camoufox handles most anti-bot checks automatically. If you still hit one:
- Wait a few seconds after `open` before the next command
- Avoid running too many sessions in parallel

**Login fails**
- Check that `MIGROS_USER` / `MIGROS_PASS` are exported correctly
- 2FA is not supported — disable it on your Migros account first

**`USER not set` / `QUERY not set`**
`sed` substitution was skipped. Verify the variables are set:
```bash
echo $MIGROS_USER
echo $MIGROS_SKILL_DIR
```

---

## Advanced: Docker (Linux servers)

`camoufox/Dockerfile` provides a self-contained image with Xvfb for headless Linux use. It bundles the same driver patch above.

```bash
docker compose up -d
```

---

## About Camoufox

[Camoufox](https://github.com/daijro/camoufox) is a patched Firefox build that spoofs browser fingerprints to evade bot detection. It runs as a local Python process and exposes a Playwright-compatible WebSocket endpoint that `playwright-cli` connects to via `cli.config.json`.

---

## License

MIT
