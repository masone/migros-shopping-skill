---
name: migros-shopping
description: Automate Migros.ch shopping — search products, build a cart, and generate a shareable list link. Use when adding products, filling a shopping cart, or creating a share link on migros.ch.
allowed-tools: Bash(python3:*), Bash(bash:*)
---

# Migros Shopping

Automate shopping on migros.ch using direct API calls via `scripts/migros-api.py`.

No browser required. Uses OAuth PKCE (same as Migros mobile app) + web session for cart operations.

## Environment

```bash
# Required — set in .env file at project root:
MIGROS_USERNAME=your@email.com
MIGROS_PASSWORD=yourpassword
MIGROS_REGION=gmzh          # See .env.example for all regions
MIGROS_ZIPCODE=8047
MIGROS_LANGUAGE=de          # de, fr, it, en (default: de)
```

Requires: `curl_cffi` (`pip install curl_cffi`)

Always use **online** context (never instore).

## Step 0 — Login

```bash
bash ./scripts/migros-login.sh
```

Result: `{"status":"login-ok","expires_in":3600}`

Tokens are cached at `~/.migros-cli/web_session.json`. Re-login only needed when refresh token expires.

## Step 1 — Create a new list

Always create a fresh list before adding products, to avoid stale items from previous runs.

```bash
python3 ./scripts/migros-api.py newlist "Einkauf 16.03."
```

Result: `{"status":"created","listId":31951246,"name":"Einkauf 16.03."}`

## Step 2 — Check current offers

```bash
bash ./scripts/migros-offers.sh
```

Result: JSON with promotions. Use this to prefer sale items when selecting products.

## Step 3 — Search products

Search in the language configured by `MIGROS_LANGUAGE` (default: German).

```bash
bash ./scripts/migros-search.sh "spaghetti"
```

Result: JSON with up to 10 results: `{ id, name, brand, description, price, quantity, promotionText }`.

The `description` field is the most important for selection — it contains fat %, UHT/pasteurised, Bio, lactose-free, etc.

**Empty results?** Try a simpler/alternative query (e.g. "laktosefreie milch" → "milch").

### Selecting the right product

Search often returns many similar products. Use these rules to pick the best match:

1. **Match the user's constraints first.** If they say "Bio Milch", only consider items whose `description` contains "Bio". If they say "laktosefrei", match that. Never substitute a conventional product when organic was requested (or vice versa).
2. **Prefer standard single-unit packs.** Pick `1l` over `6 x 1l` or `250ml` unless the user explicitly asked for a multipack or small size.
3. **Prefer items on promotion.** If `promotionText` is non-empty, prefer that product (all else being equal). Check offers first (Step 2) to know what's on sale.
4. **Prefer Migros own brands** (M-Classic, M-Budget, Migros Bio, Alnatura) for everyday staples unless the user names a specific brand.
5. **When still ambiguous, prefer the cheapest option** in the standard size.

### Search tips

- Search in the configured language. For German: use specific terms like "Rüebli" not "Karotten", "Poulet" not "Huhn".
- For compound items (e.g. "Bio Vollmilch"), search the main noun ("Vollmilch") and filter results by description.
- If a first search returns nothing relevant, try synonyms or broader terms.

## Step 4 — Add products to basket (one call per product)

Use the `id` from search results:

```bash
bash ./scripts/migros-add.sh 100005465
```

With quantity:
```bash
bash ./scripts/migros-add.sh 100005465 2
```

Result: `{"status":"added","id":"100005465","quantity":1,"listId":31798100}`

## Step 5 — Validate cart

```bash
bash ./scripts/migros-cart.sh
```

Result: JSON with basket contents and totals.

## Step 6 — Get share URL

```bash
python3 ./scripts/migros-api.py share
```

Result: `{"shareUrl":"https://www.migros.ch/list/aBcDeFgH","listId":...}`

## Summary report

At the end, always report:
- **Added:** list of successfully added products
- **Not added:** list of failed products (and why)
- **Share link:** the share URL from Step 6

## Error handling

- `"leshop-error":"expiredtoken"` → Re-login: `bash ./scripts/migros-login.sh`
- `401` on web API → Token refresh failed, re-login
- Network errors → Check `curl_cffi` is installed, check connectivity to migros.ch

## API reference

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/onesearch-oc-seaapi/public/v5/search` | POST | Bearer | Product search |
| `/product-display/public/v4/product-cards` | POST | Bearer | Product details (name, price) |
| `/shopping-list/public/v1/list` | POST | Bearer | Create new list |
| `/shopping-list/public/v1/lists/overview` | GET | Bearer | List all lists |
| `/shopping-list/public/v3/items` | PUT | Bearer | Add to online basket |
| `/shopping-list/public/v2/list/details` | GET | Bearer | Basket contents |
| `/shopping-list/public/v1/lists/{id}/invitation` | GET | Bearer | Get share link |
