async page => {
  const query = "__QUERY__";
  if (query === "__" + "QUERY__") throw new Error("QUERY not set — use sed to replace __QUERY__");
  const q = encodeURIComponent(query);
  await page.goto("https://www.migros.ch/de/search?query=" + q + "&context=ecommerce");
  await page.locator("main article").first().locator("a[href*='/de/product/']").first().click();
  await page.waitForURL("https://www.migros.ch/de/product/**");

  const id = page.url().split("/").pop().split("?")[0];

  await page.locator('button[aria-label*="Warenkorb hinzufügen"]').first().click();
  await page.locator('button:has-text("1 im Warenkorb")').first().waitFor();

  return JSON.stringify({ status: "added", query: query, id: id });
}
