async page => {
  const query = "__QUERY__";
  if (query === "__" + "QUERY__") throw new Error("QUERY not set — use sed to replace __QUERY__");
  const q = encodeURIComponent(query);
  await page.goto("https://www.migros.ch/de/search?query=" + q + "&context=ecommerce");
  const hasResults = await page.locator("main article").first().waitFor().then(() => true, () => false);
  if (!hasResults) return JSON.stringify({ query: query, results: [] }, null, 2);

  const products = await page.$$eval("main article", articles => {
    return articles.slice(0, 10).map((art, i) => {
      const nameEl = art.querySelector('[data-testid*="product-name"]');
      const nameContainer = nameEl?.parentElement?.parentElement;
      const brandAndName = nameContainer ? Array.from(nameContainer.children)
        .filter(c => c.textContent.trim() !== ",")
        .map(c => c.children.length > 0
          ? Array.from(c.children).map(cc => cc.textContent.trim()).join(", ")
          : c.textContent.trim())
        .join(" ") : "";
      const price = art.querySelector('[data-testid="current-price"]')?.textContent?.trim() || "";
      const size = art.querySelector('[data-testid="default-product-size"]')?.textContent?.trim() || "";
      const unitSpan = Array.from(art.querySelectorAll("span")).find(s => {
        const t = s.textContent.trim();
        return t.match(/^\d.*\/\d+/) && t.length < 20;
      });
      const unitPrice = unitSpan?.textContent?.trim() || "";
      const labels = Array.from(art.querySelectorAll("mo-product-picto"))
        .map(p => (p.getAttribute("data-testid") || "").replace("picto-", ""))
        .filter(Boolean);
      const href = art.querySelector("a[href*='/de/product/']")?.getAttribute("href") || "";
      const id = href.split("/").pop()?.split("?")[0] || "";
      return { index: i + 1, name: brandAndName, price: price, size: size, unitPrice: unitPrice, labels: labels, id: id };
    });
  });

  return JSON.stringify({ query: query, results: products }, null, 2);
}
