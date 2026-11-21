// Exercise the hosted shop in a new, isolated jury room.
const assert = require("node:assert/strict");
const { chromium } = require(process.env.PLAYWRIGHT_PATH || "playwright");
const base = process.env.JURY_URL || "https://egorchulanov.github.io/vk-case-2026/";
const button = (page, name) => page.getByRole("button", { name, exact: true }).first();

async function test() {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH });
  try {
    const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, colorScheme: "dark" });
    const desktop = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const buyer = await mobile.newPage();
    const seller = await desktop.newPage();
    const errors = [];
    for (const page of [buyer, seller]) {
      page.setDefaultTimeout(30000);
      page.on("pageerror", e => errors.push(e.message));
      if (process.env.JURY_DIAGNOSTICS) {
        page.on("requestfailed", r => console.error(r.method(), new URL(r.url()).pathname, r.failure()?.errorText));
        page.on("response", r => { if (r.status() >= 400) console.error(r.status(), new URL(r.url()).pathname); });
      }
      page.on("response", r => { if (r.status() >= 400) errors.push(r.status() + " " + new URL(r.url()).pathname); });
    }
    await buyer.goto(base);
    await buyer.getByRole("link", { name: "Попробовать", exact: true }).click();
    await button(buyer, "Войти как продавец").waitFor();
    await button(buyer, "Войти как покупатель").click();
    await button(buyer, "Клипы").waitFor();
    const invitation = buyer.url();
    assert.match(new URL(invitation).hash, /room=[a-f0-9]{48}/);
    await seller.goto(invitation);
    await button(seller, "Войти как продавец").click();
    await seller.getByText("Требуют внимания", { exact: true }).waitFor();
    await button(buyer, "Клипы").click();
    const video = buyer.locator("video");
    await video.evaluate(el => el.play());
    await buyer.waitForFunction(() => document.querySelector("video")?.currentTime > 0.2);
    await buyer.locator(".clip-tag").click();
    const productHeading = buyer.getByRole("heading", { name: "Кружка «Утро»" });
    await productHeading.waitFor();
    await button(buyer, "Вернуться к клипу").click();
    await buyer.getByRole("heading", { name: "Клипы сообщества" }).waitFor();
    assert.equal(buyer.url(), invitation);
    await buyer.goForward();
    await productHeading.waitFor();
    await button(buyer, "В корзину").click();
    await button(buyer, "Оформить заказ").click();
    const heading = await buyer.getByRole("heading", { name: /Заказ №/ }).innerText();
    await buyer.getByLabel("Вопрос мастерской").fill("Во сколько можно забрать кружку?");
    await button(buyer, "Отправить").click();
    await button(seller, "Сообщения").click();
    await seller.getByRole("button", { name: /Во сколько можно забрать кружку/ }).click();
    await seller.getByRole("heading", { name: heading, exact: true }).waitFor();
    assert.match(await seller.locator(".row").filter({ hasText: "Источник заказа" }).innerText(), /Клипы/);
    await seller.getByLabel("Сообщение покупателю").fill("Кружка готова, ждём до восьми.");
    await button(seller, "Отправить").click();
    await buyer.getByText("Кружка готова, ждём до восьми.", { exact: true }).waitFor();
    await button(seller, "Подтвердить выдачу").click();
    await buyer.locator(".chip").filter({ hasText: "Выдан" }).waitFor();
    if (process.env.JURY_ORDER_SCREENSHOT) {
      await buyer.evaluate(() => window.scrollTo(0, 0));
      await buyer.screenshot({ path: process.env.JURY_ORDER_SCREENSHOT, animations: "disabled" });
    }
    await buyer.reload();
    await button(buyer, "Мои заказы").click();
    const orderNumber = heading.replace("Заказ ", "");
    await buyer.getByRole("button", { name: new RegExp(orderNumber) }).getByText("Выдан").waitFor();
    // A new browser that opens the jury page gets its own shop.
    const other = await browser.newPage();
    await other.goto(new URL("prototype/", base).href);
    await button(other, "Войти как покупатель").click();
    await button(other, "Мои заказы").click();
    assert.notEqual(new URL(other.url()).hash, new URL(invitation).hash);
    assert.equal(await other.getByText("Кружка готова, ждём до восьми.", { exact: true }).count(), 0);
    assert.equal(await other.getByRole("button", { name: new RegExp(orderNumber) }).count(), 0);
    assert.deepEqual(errors, []);
    console.log("Проверены кнопка жюри, оба входа, клип, заказ, переписка, выдача, сохранение статуса и отдельный магазин для нового посетителя.");
  } finally {
    await browser.close();
  }
}

test().catch(e => { console.error(e); process.exitCode = 1; });
