# migros-shopping

An AI agent skill that automates shopping on [migros.ch](https://www.migros.ch) — search products, build a cart and yes it could press the order button For you. I prefer to get a cart sharing link and order in a separate account.

---

## Requirements

- Node.js 18+
- A Playwright-compatible browser server at `ws://localhost:9222/browser`
- A Migros account with no MFA and an addres set in your profile (to determine product availability in your delivery region)

If you're getting a maintenance page, you're running into bot protection. I've had good results with [Camoufox](https://github.com/daijro/camoufox) — an anti-detect Firefox build that circumvents Migros' bot protection well. Chrome on OSX is working as well, but hasn't worked for me on Ubuntu.

---

## Setup

```bash
npm install
```

Make sure these environment variables are set:

```bash
export MIGROS_USER="your@email.com"
export MIGROS_PASS="yourpassword"
export PATH="$PATH:/path/to/migros-shopping-skill/node_modules/.bin"
export PLAYWRIGHT_MCP_CONFIG="/path/to/migros-shopping-skill/cli.config.json"
```

Edit `cli.config.json` to match your browser server (ie. `remoteEndpoint`, `browserName`).

---

## Usage

Start your browser server, then ask Claude:

> "Fill my Migros cart with: lactose free milk, spaghetti, tomatoes, bread, and butter."

Export your order history and have the LLM pick from your prefered products. Using IDs works as well:

> "Fill my migros cart with: 204016500000, 104125000000"

**OpenClaw** — drop this directory into your skills folder. `SKILL.md` is discovered automatically.

