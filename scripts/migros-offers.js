async page => {
  await page.goto("https://www.migros.ch/de/offers/home?context=ecommerce");
  await page.keyboard.press("Escape").catch(() => {});
  const hasOffers = await page.locator("main article.product-card").first().waitFor().then(() => true, () => false);
  if (!hasOffers) return JSON.stringify({ offers: [] });

  const offers = await page.$$eval("main article.product-card", articles => {
    return articles.slice(0, 30).map(art => {
      const nameEl = art.querySelector('[data-testid*="product-name"]');
      const nameContainer = nameEl?.parentElement?.parentElement;
      const name = nameContainer ? Array.from(nameContainer.children)
        .filter(c => c.textContent.trim() !== ",")
        .map(c => c.children.length > 0
          ? Array.from(c.children).map(cc => cc.textContent.trim()).join(", ")
          : c.textContent.trim())
        .join(" ") : "";
      const price = art.querySelector('[data-testid="current-price"]')?.textContent?.trim() || "";
      const oldPrice = art.querySelector('[data-testid="original-price"]')?.textContent?.trim() || "";
      const discount = art.querySelector('[data-testid="description"]')?.textContent?.trim() || "";
      const size = art.querySelector('[data-testid="default-product-size"]')?.textContent?.trim() || "";
      const href = art.querySelector("a[href*='/de/product/']")?.getAttribute("href") || "";
      const id = href.split("/").pop()?.split("?")[0] || "";
      return { name, price, oldPrice, discount, size, id };
    }).filter(o => o.name);
  });

  return JSON.stringify({ offers }, null, 2);
}
