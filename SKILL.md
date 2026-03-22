---
name: migros-shopping
description: "Grocery shopping on Migros.ch — create a shopping list (Einkaufsliste), search and add products to cart, check offers, and get a share link. Use for weekly shopping, buying groceries, filling a Migros cart, building a grocery list, or any Migros-related shopping task."
allowed-tools: Bash(python3:*), Bash(bash:*)
---

# Migros Shopping

Automate shopping on migros.ch using direct API calls via `scripts/migros-api.py`.

No browser required. Uses OAuth PKCE (same as Migros mobile app) + web session for cart operations.

## Environment

Configure `.env` at project root (see `.env.example` for all options). Required: `MIGROS_USERNAME`, `MIGROS_PASSWORD`, `MIGROS_REGION`, `MIGROS_ZIPCODE`.

### Dependencies

The API client needs `curl_cffi` (a Python HTTP library that can impersonate browser TLS fingerprints, which is required to pass Migros's Cloudflare protection). Before the first run, check if it's installed and install if missing:

```bash
python3 -c "import curl_cffi" 2>/dev/null || pip install curl_cffi
```

Always use **online** context (never instore).

## Before You Start

1. Check if `memory/migros/products.md` exists — it has verified product IDs (format `100XXXXXX`). Use those IDs directly in Step 4, skipping search. This saves significant time since search requires a web session warm-up per call.
2. IDs without the `100` prefix are from an old format — ask the user to update them.

---

## Step 0 — Login

Always run login — it's fast and handles its own token caching. Don't try to guess whether a session exists.

```bash
bash ./scripts/migros-login.sh
```

Result: `{"status":"login-ok","expires_in":3600}`

## Step 1 — Create a new list

Always create a fresh list before adding products (reusing old lists causes duplicate items and stale pricing).

```bash
python3 ./scripts/migros-api.py newlist "Einkauf $(date +%d.%m.)"
```

Result: `{"status":"created","listId":31951246,"name":"Einkauf 22.03."}`

## Step 2 — Check current offers

Check offers before searching so you can prefer sale items when selecting products.

```bash
bash ./scripts/migros-offers.sh
```

Result: JSON with promotions: `{ id, name, brand, price, quantity, promotionText }`.

## Step 3 — Search products

Search in the language configured by `MIGROS_LANGUAGE` (default: German).

```bash
bash ./scripts/migros-search.sh "spaghetti"
```

Result: JSON with up to 10 results: `{ id, name, brand, description, price, quantity, promotionText }`.

The `description` field is the most important for selection — it contains fat %, UHT/pasteurised, Bio, lactose-free, etc.

**Empty results?** Try a simpler/alternative query (e.g. "laktosefreie milch" -> "milch").

### Selecting the right product

Search often returns many similar products. Use these rules to pick the best match:

1. **Match the user's constraints first.** If they say "Bio Milch", only consider items whose `description` contains "Bio". If they say "laktosefrei", match that. Never substitute a conventional product when organic was requested (or vice versa).
2. **Prefer standard single-unit packs.** Pick `1l` over `6 x 1l` or `250ml` unless the user explicitly asked for a multipack or small size. Multipacks are often store-only and fail to add online.
3. **Prefer items on promotion.** If `promotionText` is non-empty, prefer that product (all else being equal).
4. **When still ambiguous,** prefer Migros own brands (M-Classic, M-Budget, Migros Bio, Alnatura) for everyday staples, and pick the cheapest standard-size option.

### Search tips

Search in the configured language (e.g., "Ruebli" not "Karotten", "Poulet" not "Huhn"). For compound terms like "Bio Vollmilch", search the main noun ("Vollmilch") and filter results by description. If no results, try synonyms or broader terms.

### Recipes and meal plans

If the user provides a recipe or meal plan, extract the ingredient list first, then process each ingredient through the normal search flow. Use reasonable default quantities (e.g., 1 pack butter, 500g pasta) unless the recipe specifies amounts.

## Step 4 — Add products to basket (one call per product)

Use the `id` from search results or the product catalog:

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
- **Added:** list of successfully added products with names and prices
- **Not added:** list of failed products (and why)
- **Share link:** the share URL from Step 6

## Maintaining the product catalog

After a successful run, update `memory/migros/products.md` with any newly discovered products the user is likely to re-order. This lets future runs skip search entirely for known products.

Format:
```markdown
| Product | ID | Brand | Notes |
|---|---|---|---|
| Vollmilch UHT 1l | 100005465 | M-Classic | Standard milk |
| Spaghetti 500g | 100012345 | M-Classic | |
```

Create the file if it doesn't exist. Only store products with verified `100XXXXXX` IDs.

## Error handling

- `"leshop-error":"expiredtoken"` or `401` on web API -> Re-login: `bash ./scripts/migros-login.sh`
- Add returns error with unknown ID -> Product may be store-only or discontinued. Search for an alternative.
- List not found error -> List was deleted externally. Create a new one (Step 1).
- `429` or rate limiting -> Wait 5 seconds and retry once.
- Network errors -> Check `curl_cffi` is installed, check connectivity to migros.ch.
