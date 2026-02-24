---
name: migros-shopping
description: Automate Migros.ch shopping — search products, build a cart, and generate a shareable list link. Use when adding products, filling a shopping cart, or creating a share link on migros.ch.
allowed-tools: Bash(playwright-cli:*)
---

# Migros Shopping

Automate shopping on migros.ch using low-token browser automation via `playwright-cli`.

All scripts are inlined below. Credentials are read from environment variables.

## Environment

```bash
# Required — set in your shell profile:
export MIGROS_USER="your@email.com"
export MIGROS_PASS="yourpassword"
export PATH="$PATH:/path/to/migros-shopping-skill/node_modules/.bin"
export PLAYWRIGHT_MCP_CONFIG="/path/to/migros-shopping-skill/cli.config.json"
```

Requires a browser accessible at `ws://localhost:9222/browser` (see README for options).

## Step 1 — Login, create new list, get share URL (once per session)

```bash
playwright-cli open
playwright-cli run-code 'async page => {
  const user = process.env.MIGROS_USER;
  const pass = process.env.MIGROS_PASS;
  if (!user || !pass) throw new Error("MIGROS_USER or MIGROS_PASS not set");
  page.setDefaultTimeout(15000);
  page.setDefaultNavigationTimeout(15000);
  const log = [];

  await page.context().clearCookies();
  await page.goto("https://login.migros.ch/login/email");
  await page.getByRole("textbox", { name: /e-mail|email/i }).fill(user);
  await page.getByRole("button", { name: /weiter|continue/i }).click();
  await page.waitForURL("**/login/password");
  await page.locator("input[type=password]").fill(pass);
  await page.getByRole("button", { name: /anmelden|log in/i }).click();
  await page.waitForURL("https://account.migros.ch/account");
  log.push("login-ok");

  page.setDefaultTimeout(6000);
  page.setDefaultNavigationTimeout(6000);

  await page.goto("https://www.migros.ch/de/shopping-list?context=ecommerce");
  const menuTrigger = page.locator("button.shopping-list-context-menu-trigger, button[aria-label*=\"Optionen anzeigen\"]").first();

  await menuTrigger.click();
  await page.getByRole("menuitem", {name: /neu.*erstellen|create new/i}).click();
  const nameInput = page.getByRole("textbox", {name: /listenname/i});
  await nameInput.fill(new Date().toLocaleDateString("de-CH", {day:"2-digit",month:"2-digit"}));
  await page.getByRole("button", {name: /neu erstellen|create/i}).click();
  log.push("list-created");

  await page.goto("https://www.migros.ch/de/shopping-list?context=ecommerce");
  await menuTrigger.click();
  await page.getByRole("menuitem", {name: /teilen|share/i}).click();
  const shareUrl = await page.waitForFunction(
    () => document.querySelector("input[aria-label=\"shared link\"]")?.value || ""
  ).then(h => h.jsonValue());
  await page.keyboard.press("Escape");
  log.push("share-url:" + shareUrl);

  return log.join("\n");
}'
```

Result: `login-ok`, `list-created`, and `share-url:<url>`.
Remember the share URL — hand it to the user at the end.

## Step 1b — Check current offers (optional)

```bash
playwright-cli run-code 'async page => {
  await page.goto("https://www.migros.ch/de/offers/home?context=ecommerce");
  await page.keyboard.press("Escape").catch(() => {});
  const hasOffers = await page.locator("main article.product-card").first().waitFor().then(() => true, () => false);
  if (!hasOffers) return JSON.stringify({ offers: [] });

  const offers = await page.$$eval("main article.product-card", articles => {
    return articles.slice(0, 30).map(art => {
      const nameEl = art.querySelector("[data-testid*=\"product-name\"]");
      const nameContainer = nameEl?.parentElement?.parentElement;
      const name = nameContainer ? Array.from(nameContainer.children)
        .filter(c => c.textContent.trim() !== ",")
        .map(c => c.children.length > 0
          ? Array.from(c.children).map(cc => cc.textContent.trim()).join(", ")
          : c.textContent.trim())
        .join(" ") : "";
      const price = art.querySelector("[data-testid=\"current-price\"]")?.textContent?.trim() || "";
      const oldPrice = art.querySelector("[data-testid=\"original-price\"]")?.textContent?.trim() || "";
      const discount = art.querySelector("[data-testid=\"description\"]")?.textContent?.trim() || "";
      const size = art.querySelector("[data-testid=\"default-product-size\"]")?.textContent?.trim() || "";
      const href = art.querySelector("a[href*=\"/de/product/\"]")?.getAttribute("href") || "";
      const id = href.split("/").pop()?.split("?")[0] || "";
      return { name, price, oldPrice, discount, size, id };
    }).filter(o => o.name);
  });

  return JSON.stringify({ offers }, null, 2);
}'
```

Result: JSON with up to 30 offers: `{ name, price, oldPrice, discount, size, id }`.
Use this to prefer sale items when selecting products.

## Step 2 — Add products (one call per product)

### 2a — By product ID (fully programmatic, cheapest)

Replace `5373798` with the actual product ID:

```bash
playwright-cli run-code 'async page => {
  const query = "5373798";
  const q = encodeURIComponent(query);
  await page.goto("https://www.migros.ch/de/search?query=" + q + "&context=ecommerce");
  await page.locator("main article").first().locator("a[href*=\"/de/product/\"]").first().click();
  await page.waitForURL("https://www.migros.ch/de/product/**");

  const id = page.url().split("/").pop().split("?")[0];

  await page.locator("button[aria-label*=\"Warenkorb hinzufügen\"]").first().click();
  await page.locator("button:has-text(\"1 im Warenkorb\")").first().waitFor();

  return JSON.stringify({ status: "added", query: query, id: id });
}'
```

Result: `{"status":"added","query":"5373798","id":"5373798"}`

### 2b — By text search, then pick (for unknown product IDs)

Always search in **German** — Migros.ch is a Swiss German site.

**Search** — replace `spaghetti` with the actual search term:

```bash
playwright-cli run-code 'async page => {
  const query = "spaghetti";
  const q = encodeURIComponent(query);
  await page.goto("https://www.migros.ch/de/search?query=" + q + "&context=ecommerce");
  const hasResults = await page.locator("main article").first().waitFor().then(() => true, () => false);
  if (!hasResults) return JSON.stringify({ query: query, results: [] }, null, 2);

  const products = await page.$$eval("main article", articles => {
    return articles.slice(0, 10).map((art, i) => {
      const nameEl = art.querySelector("[data-testid*=\"product-name\"]");
      const nameContainer = nameEl?.parentElement?.parentElement;
      const brandAndName = nameContainer ? Array.from(nameContainer.children)
        .filter(c => c.textContent.trim() !== ",")
        .map(c => c.children.length > 0
          ? Array.from(c.children).map(cc => cc.textContent.trim()).join(", ")
          : c.textContent.trim())
        .join(" ") : "";
      const price = art.querySelector("[data-testid=\"current-price\"]")?.textContent?.trim() || "";
      const size = art.querySelector("[data-testid=\"default-product-size\"]")?.textContent?.trim() || "";
      const unitSpan = Array.from(art.querySelectorAll("span")).find(s => {
        const t = s.textContent.trim();
        return t.match(/^\d.*\/\d+/) && t.length < 20;
      });
      const unitPrice = unitSpan?.textContent?.trim() || "";
      const labels = Array.from(art.querySelectorAll("mo-product-picto"))
        .map(p => (p.getAttribute("data-testid") || "").replace("picto-", ""))
        .filter(Boolean);
      const href = art.querySelector("a[href*=\"/de/product/\"]")?.getAttribute("href") || "";
      const id = href.split("/").pop()?.split("?")[0] || "";
      return { index: i + 1, name: brandAndName, price: price, size: size, unitPrice: unitPrice, labels: labels, id: id };
    });
  });

  return JSON.stringify({ query: query, results: products }, null, 2);
}'
```

Result: JSON array with up to 10 results: `{ index, name, price, size, unitPrice, labels, id }`.
- `labels`: product badges like `["BIO", "REGION", "FRESHNESS"]`

**Empty results?** Try once with a simpler/alternative query (e.g. "laktosefreie milch" → "milch"), then pick the best match.

**Pick** the best result by index — replace `1` with the actual index (products sorted by relevance; best match is usually top 3):

```bash
playwright-cli run-code 'async page => {
  const pickIndex = 1;
  const idx = pickIndex - 1;
  await page.locator("main article").nth(idx).locator("a[href*=\"/de/product/\"]").first().click();
  await page.waitForURL("https://www.migros.ch/de/product/**");

  const id = page.url().split("/").pop().split("?")[0];

  await page.locator("button[aria-label*=\"Warenkorb hinzufügen\"]").first().click();
  await page.locator("button:has-text(\"1 im Warenkorb\")").first().waitFor();

  return JSON.stringify({ status: "added", index: pickIndex, id: id });
}'
```

Result: `{"status":"added","index":1,"id":"..."}`

## Step 3 — Validate cart

```bash
playwright-cli run-code 'async page => {
  await page.goto("https://www.migros.ch/de/shopping-list?context=ecommerce");
  const hasItems = await page.locator("[data-testid=\"basket-total\"]").waitFor().then(() => true, () => false);
  if (!hasItems) return JSON.stringify({ items: 0, total: "0.00" });

  const total = await page.locator("[data-testid=\"basket-total\"]").textContent().then(t => t.trim());
  const items = await page.locator("main article.product-card").count();

  return JSON.stringify({ items, total });
}'
```

Result: `{"items":42,"total":"187.50"}`

## Step 4 — Close browser

```bash
playwright-cli close
```

Always close when done to free the remote browser session.

## Summary report

At the end, always report:
- **Added:** list of successfully added products
- **Not added:** list of failed products (and why)
- **Share link:** the share URL from Step 1

---

## playwright-cli Reference

`playwright-cli` controls the remote browser. Each command returns a snapshot of the page with element references (`e1`, `e2`, ...).

### Core commands

```bash
playwright-cli open
playwright-cli open https://example.com
playwright-cli goto https://example.com
playwright-cli snapshot
playwright-cli click e5
playwright-cli fill e3 "search query"
playwright-cli type "text"
playwright-cli press Enter
playwright-cli eval "document.title"
playwright-cli screenshot
playwright-cli close
```

### Navigation

```bash
playwright-cli go-back
playwright-cli go-forward
playwright-cli reload
playwright-cli resize 1920 1080
```

### run-code — arbitrary Playwright code (token-efficient)

Use `run-code` for complex operations that return only the result (~50–200 bytes vs 60–275 KB for snapshot):

```bash
playwright-cli run-code 'async page => {
  await page.goto("https://example.com");
  return await page.title();
}'
```

### Storage

```bash
playwright-cli state-save auth.json
playwright-cli state-load auth.json
playwright-cli cookie-list
playwright-cli cookie-get session_id
```

### Multiple sessions

```bash
# Isolate browser contexts with -s flag:
playwright-cli-s=cart open
playwright-cli-s=cart goto https://migros.ch
playwright-cli close-all
```

## Error handling

- If a script fails, inspect `### Error` in the output.
- Use `snapshot` as a last resort for debugging — it returns the full page tree.
- Bot protection: migros.ch uses bot detection. After `open`/`goto`, wait 5–8s before the next command if needed. An anti-detect browser (see README) handles most cases automatically.
- Use `run-code` with `page.setDefaultTimeout(15000)` for slow pages.
