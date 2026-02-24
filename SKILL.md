---
name: migros-shopping
description: Automate Migros.ch shopping — search products, build a cart, and generate a shareable list link. Uses Camoufox anti-detect browser to bypass bot protection. Use when adding products, filling a shopping cart, or creating a share link on migros.ch.
allowed-tools: Bash(playwright-cli:*)
---

# Migros Shopping

Automate shopping on migros.ch using low-token browser automation via `playwright-cli`. The Camoufox anti-detect Firefox browser is required to bypass bot protection.

Scripts live in `./scripts/`. Variables are injected via `sed`, output comes back as `### Result`.

## Environment

```bash
# Required — set in your shell profile:
export MIGROS_SKILL_DIR="/absolute/path/to/migros-shopping-skill"
export MIGROS_USER="your@email.com"
export MIGROS_PASS="yourpassword"
export PATH="$PATH:$MIGROS_SKILL_DIR/node_modules/.bin"

# Start the browser server (once per session):
python3 "$MIGROS_SKILL_DIR/camoufox/launch_server.py" &
```

All `playwright-cli` commands pass `--config "$MIGROS_SKILL_DIR/cli.config.json"` to use the bundled Camoufox config.

## Step 1 — Login, create new list, get share URL (once per session)

```bash
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" open --headed
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" resize 1600 1200
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" run-code 'async page => { page.setDefaultTimeout(6000); page.setDefaultNavigationTimeout(6000); }'
sed "s|__USER__|$MIGROS_USER|g;s|__PASS__|$MIGROS_PASS|g" "$MIGROS_SKILL_DIR/scripts/migros-login.js" | xargs -0 playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" run-code
```

Result: `login-ok`, `list-created`, and `share-url:<url>`.
Remember the share URL — hand it to the user at the end.

## Step 1b — Check current offers (optional)

```bash
cat "$MIGROS_SKILL_DIR/scripts/migros-offers.js" | xargs -0 playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" run-code
```

Result: JSON with up to 30 offers: `{ name, price, oldPrice, discount, size, id }`.
Use this to prefer sale items when selecting products.

## Step 2 — Add products (one call per product)

### 2a — By product ID (fully programmatic, cheapest)

```bash
sed "s|__QUERY__|5373798|g" "$MIGROS_SKILL_DIR/scripts/migros-add.js" | xargs -0 playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" run-code
```

Result: `{"status":"added","query":"5373798","id":"5373798"}`

### 2b — By text search, then pick (for unknown product IDs)

Always search in **German** — Migros.ch is a Swiss German site.

**Search:**
```bash
sed "s|__QUERY__|spaghetti|g" "$MIGROS_SKILL_DIR/scripts/migros-search.js" | xargs -0 playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" run-code
```

Result: JSON array with up to 10 results: `{ index, name, price, size, unitPrice, labels, id }`.
- `labels`: product badges like `["BIO", "REGION", "FRESHNESS"]`

**Empty results?** Try once with a simpler/alternative query (e.g. "laktosefreie milch" → "milch"), then pick the best match.

**Pick** the best result by index (products are sorted by relevance; best match is usually top 3):
```bash
sed "s|__INDEX__|1|g" "$MIGROS_SKILL_DIR/scripts/migros-pick.js" | xargs -0 playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" run-code
```

Result: `{"status":"added","index":1,"id":"..."}`

## Step 3 — Validate cart

```bash
cat "$MIGROS_SKILL_DIR/scripts/migros-cart.js" | xargs -0 playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" run-code
```

Result: `{"items":42,"total":"187.50"}`

## Step 4 — Close browser

```bash
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" close
```

Always close when done to free the remote browser session.

## Summary report

At the end, always report:
- **Added:** list of successfully added products
- **Not added:** list of failed products (and why)
- **Share link:** the share URL from Step 1

---

## playwright-cli Reference

`playwright-cli` controls the Camoufox browser. Each command returns a snapshot of the page with element references (`e1`, `e2`, ...).

### Core commands

```bash
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" open
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" open https://example.com
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" goto https://example.com
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" snapshot
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" click e5
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" fill e3 "search query"
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" type "text"
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" press Enter
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" eval "document.title"
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" screenshot
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" close
```

### Navigation

```bash
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" go-back
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" go-forward
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" reload
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" resize 1920 1080
```

### run-code — arbitrary Playwright code (token-efficient)

Use `run-code` for complex operations that return only the result (~50–200 bytes vs 60–275 KB for snapshot):

```bash
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" run-code "async page => {
  await page.goto('https://example.com');
  return await page.title();
}"

# Or pipe a script file:
cat script.js | xargs -0 playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" run-code
```

### Storage

```bash
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" state-save auth.json
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" state-load auth.json
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" cookie-list
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" cookie-get session_id
```

### Multiple sessions

```bash
# Isolate browser contexts with -s flag:
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" -s=cart open
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" -s=cart goto https://migros.ch
playwright-cli --config "$MIGROS_SKILL_DIR/cli.config.json" close-all
```

## Error handling

- If a script fails, inspect `### Error` in the output.
- Use `snapshot` as a last resort for debugging — it returns the full page tree.
- Bot protection: Camoufox spoofs fingerprints automatically. After `open`/`goto` on protected pages, wait 5–8s before the next command if needed.
- Use `run-code` with `page.setDefaultTimeout(15000)` for slow pages.
