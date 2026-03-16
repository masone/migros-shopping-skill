---
name: migros-shopping
description: Automate Migros.ch shopping — search products, build a cart, and generate a shareable list link. Use when adding products, filling a shopping cart, or creating a share link on migros.ch.
allowed-tools: Bash(playwright-cli:*), Bash(sed:*), Bash(cat:*), Bash(xargs:*)
---

# Migros Shopping

Automate shopping on migros.ch using `playwright-cli` with run-code scripts for low token usage.

Scripts live in `./scripts/`. Variables are injected via `sed`, output comes back as `### Result`.

## Environment

```bash
# Required — set in your shell:
export MIGROS_USER="your@email.com"
export MIGROS_PASS="yourpassword"
# Ensure playwright-cli is in PATH:
export PATH="$PATH:/path/to/migros-shopping-skill/node_modules/.bin"
```

Requires a Chromium browser accessible at the CDP endpoint in `cli.config.json`.

## Step 1 — Open browser

```bash
playwright-cli --config cli.config.json open
```

## Step 2 — Login, create new list, get share URL

```bash
sed "s|__USER__|$MIGROS_USER|g;s|__PASS__|$MIGROS_PASS|g" ./scripts/migros-login.js | xargs -0 playwright-cli --config cli.config.json run-code
```

Result: `login-ok`, `list-created`, and `share-url:<url>`.
Remember the share URL — hand it to the user at the end.

## Step 3 — Check current offers (optional)

```bash
cat ./scripts/migros-offers.js | xargs -0 playwright-cli --config cli.config.json run-code
```

Result: JSON with up to 30 offers: `{ name, price, oldPrice, discount, size, id }`.
Use this to prefer sale items when selecting products.

## Step 4 — Add products (one call per product)

### 4a — By product ID (fully programmatic)

```bash
sed "s|__QUERY__|5373798|g" ./scripts/migros-add.js | xargs -0 playwright-cli --config cli.config.json run-code
```

Result: `{"status":"added","query":"5373798","id":"5373798"}`

### 4b — By text search, then pick

Always search in **German** — Migros.ch is a Swiss German site.

**Search:**
```bash
sed "s|__QUERY__|spaghetti|g" ./scripts/migros-search.js | xargs -0 playwright-cli --config cli.config.json run-code
```

Result: JSON array with up to 10 results: `{ index, name, price, size, unitPrice, labels, id }`.
- `labels`: product badges like `["BIO", "REGION", "FRESHNESS"]`

**Empty results?** Try once with a simpler/alternative query (e.g. "laktosefreie milch" → "milch"), then pick the best match.

**Pick** the best result by index (products are sorted by relevance; best match is usually top 3):
```bash
sed "s|__INDEX__|1|g" ./scripts/migros-pick.js | xargs -0 playwright-cli --config cli.config.json run-code
```

Result: `{"status":"added","index":1,"id":"..."}`

## Step 5 — Validate cart

```bash
cat ./scripts/migros-cart.js | xargs -0 playwright-cli --config cli.config.json run-code
```

Result: `{"items":42,"total":"187.50"}`

## Step 6 — Close browser

```bash
playwright-cli --config cli.config.json close
```

Always close when done to free the browser session.

## Summary report

At the end, always report:
- **Added:** list of successfully added products
- **Not added:** list of failed products (and why)
- **Share link:** the share URL from Step 2

## Error handling

- If a script fails, inspect `### Error` in the output.
- Use `playwright-cli --config cli.config.json snapshot` as a last resort for debugging.
- Bot protection: migros.ch uses bot detection. After `open`/`goto`, wait 5–8s before the next command if needed.
