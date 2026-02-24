async page => {
  await page.goto("https://www.migros.ch/de/shopping-list?context=ecommerce");
  const hasItems = await page.locator('[data-testid="basket-total"]').waitFor().then(() => true, () => false);
  if (!hasItems) return JSON.stringify({ items: 0, total: "0.00" });

  const total = await page.locator('[data-testid="basket-total"]').textContent().then(t => t.trim());
  const items = await page.locator("main article.product-card").count();

  return JSON.stringify({ items, total });
}
