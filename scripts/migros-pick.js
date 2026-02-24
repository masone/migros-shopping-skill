async page => {
  if (typeof __INDEX__ !== "number" || __INDEX__ < 1) throw new Error("INDEX not set or invalid — use sed to replace __INDEX__ with a positive integer");
  const idx = __INDEX__ - 1;
  await page.locator("main article").nth(idx).locator("a[href*='/de/product/']").first().click();
  await page.waitForURL("https://www.migros.ch/de/product/**");

  const id = page.url().split("/").pop().split("?")[0];

  await page.locator('button[aria-label*="Warenkorb hinzufügen"]').first().click();
  await page.locator('button:has-text("1 im Warenkorb")').first().waitFor();

  return JSON.stringify({ status: "added", index: __INDEX__, id: id });
}
