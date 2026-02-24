async page => {
  const user = "__USER__";
  const pass = "__PASS__";
  if (user === "__" + "USER__") throw new Error("USER not set — use sed to replace __USER__");
  if (pass === "__" + "PASS__") throw new Error("PASS not set — use sed to replace __PASS__");

  page.setDefaultTimeout(15000);
  page.setDefaultNavigationTimeout(15000);
  const log = [];

  // login
  await page.context().clearCookies();
  await page.goto("https://login.migros.ch/login/email");
  await page.getByRole("textbox", { name: /e-mail|email/i }).fill(user);
  await page.getByRole("button", { name: /weiter|continue/i }).click();
  await page.waitForURL("**/login/password");
  await page.locator("input[type=password]").fill(pass);
  await page.getByRole("button", { name: /anmelden|log in/i }).click();
  await page.waitForURL("https://account.migros.ch/account");
  log.push("login-ok");

  // tighten back after slow login
  page.setDefaultTimeout(6000);
  page.setDefaultNavigationTimeout(6000);

  // shopping list
  await page.goto("https://www.migros.ch/de/shopping-list?context=ecommerce");  
  const menuTrigger = page.locator('button.shopping-list-context-menu-trigger, button[aria-label*="Optionen anzeigen"]').first();
  
  // create new list
  await menuTrigger.click();
  await page.getByRole("menuitem", {name: /neu.*erstellen|create new/i}).click();
  const nameInput = page.getByRole("textbox", {name: /listenname/i});
  await nameInput.fill(new Date().toLocaleDateString("de-CH", {day:"2-digit",month:"2-digit"}));
  await page.getByRole("button", {name: /neu erstellen|create/i}).click();
  log.push("list-created");

  // reload to clear modal overlay, then share
  await page.goto("https://www.migros.ch/de/shopping-list?context=ecommerce");
  await menuTrigger.click();
  await page.getByRole("menuitem", {name: /teilen|share/i}).click();
  const shareUrl = await page.waitForFunction(
    () => document.querySelector('input[aria-label="shared link"]')?.value || "",
  ).then(h => h.jsonValue());
  await page.keyboard.press("Escape");
  log.push("share-url:" + shareUrl);

  return log.join("\n");
}
