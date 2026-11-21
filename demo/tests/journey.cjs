/* Verify the two independent shop sessions using an isolated database. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const net = require("node:net");
const { spawn } = require("node:child_process");
const { chromium } = require(process.env.PLAYWRIGHT_PATH || "playwright");
const demo = path.resolve(__dirname, "..");
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "vk-shop-test-"));
const screenshots = process.env.SHOP_SCREENSHOTS;
const button = (page, name) =>
  page.getByRole("button", { name, exact: true }).first();

async function assertNavFits(page) {
  const nav = page.locator("nav");
  await nav.waitFor();
  assert.equal(await nav.getByRole("button").count(), 6);
  assert(await nav.evaluate(el => el.scrollWidth <= el.clientWidth &&
    [...el.querySelectorAll("button")].every(b => {
      const rect = b.getBoundingClientRect();
      return rect.left >= 0 && rect.right <= window.innerWidth && rect.height >= 40;
    })
  ), "Все шесть разделов должны быть видны без горизонтальной прокрутки");
}

async function port() {
  const socket = net.createServer();
  await new Promise((resolve) => socket.listen(0, "127.0.0.1", resolve));
  const p = socket.address().port;
  await new Promise((resolve) => socket.close(resolve));
  return p;
}
async function capture(page, name) {
  if (!screenshots) return;
  fs.mkdirSync(screenshots, { recursive: true });
  await page.evaluate(async () => {
    await document.fonts.ready;
    window.scrollTo(0, 0);
  });
  await page.screenshot({
    path: path.join(screenshots, name + ".png"),
    animations: "disabled",
  });
}
(async () => {
  let browser, server;
  const p = await port(),
    origin = "http://127.0.0.1:" + p;
  try {
    server = spawn(
      process.env.SHOP_PYTHON || path.join(demo, ".venv/bin/python"),
      [
        "-m",
        "uvicorn",
        "server:app",
        "--host",
        "127.0.0.1",
        "--port",
        String(p),
      ],
      {
        cwd: demo,
        env: { ...process.env, SHOP_DB: path.join(temporary, "test.sqlite3") },
        stdio: ["ignore", "ignore", "pipe"],
      },
    );
    let diagnostic = "";
    server.stderr.on("data", (chunk) => {
      diagnostic += chunk;
    });
    let ready = false;
    for (let i = 0; i < 100; i++) {
      if (server.exitCode != null) throw Error(diagnostic);
      try {
        if ((await fetch(origin)).ok) {
          ready = true;
          break;
        }
      } catch {}
      await new Promise((done) => setTimeout(done, 150));
    }
    assert(ready, diagnostic || "Shop did not start");
    browser = await chromium.launch({
      headless: true,
      executablePath: process.env.CHROMIUM_PATH,
    });
    const seller = await browser.newPage({
        viewport: { width: 1440, height: 900 },
      }),
      buyer = await browser.newPage({ viewport: { width: 390, height: 844 }, colorScheme: "dark" });
    const errors = [];
    for (const page of [seller, buyer]) {
      page.setDefaultTimeout(12000);
      page.on("pageerror", (e) => errors.push(String(e)));
      await page.goto(origin);
    }
    await button(buyer, "Войти как покупатель").waitFor();
    await buyer.evaluate(() => document.fonts.ready);
    for (const label of ["Войти как продавец", "Войти как покупатель"]) {
      const box = await button(buyer, label).boundingBox();
      assert(box && box.y + box.height <= 844 && box.x >= 0 && box.x + box.width <= 390, label);
    }
    assert.deepEqual(await buyer.locator(".login h1").evaluate(el => {
      const style = getComputedStyle(el);
      return [style.color, style.fontFamily.includes("VK Sans Text"), document.fonts.check('600 20px "VK Sans Text"')];
    }), ["rgb(25, 35, 46)", true, true]);
    await capture(buyer, "roles");
    await button(seller, "Войти как продавец").click();
    await button(buyer, "Войти как покупатель").click();
    await seller.getByText("Требуют внимания", { exact: true }).waitFor();
    await capture(seller, "overview");
    await seller.getByRole("button", { name: /Подготовить товар/ }).click();
    await seller.getByLabel("Адрес самовывоза").fill("Мастерская на Покровке");
    await seller
      .getByLabel("Текст записи")
      .fill("Новая партия кружек с молочной глазурью готова к самовывозу.");
    await button(seller, "Опубликовать").click();
    await button(seller, "Публикации").click();
    await button(seller, "Новая запись").click();
    await seller.getByLabel("Товар из витрины").selectOption("1");
    const post =
      "Кружка «Мел» после обжига. Показываем глазурь при дневном свете.";
    await seller.getByLabel("Текст публикации").fill(post);
    await button(seller, "Опубликовать запись").click();
    await seller.locator("button.pub-item").filter({ hasText: post }).click();
    await buyer.reload();
    const feed = buyer.locator(".feed-post").filter({ hasText: post });
    await feed.getByRole("button", { name: "Открыть товар" }).click();
    await buyer.getByRole("heading", { name: "Кружка «Мел»" }).waitFor();
    await capture(buyer, "card");
    await button(buyer, "Сохранить").click();
    await button(buyer, "В сохранённых").waitFor();
    assert((await buyer.locator(".vkuiButton__content").first().evaluate(el => getComputedStyle(el).fontFamily)).includes("VK Sans Text"));
    await button(buyer, "В корзину").click();
    await button(buyer, "Оформить заказ").click();
    const title = await buyer
      .getByRole("heading", { name: /Заказ №/ })
      .innerText();
    await buyer
      .getByLabel("Вопрос мастерской")
      .fill("Можно забрать сегодня после шести?");
    await button(buyer, "Отправить").click();
    await button(seller, "Сообщения").click();
    await seller.getByRole("button", { name: /Можно забрать сегодня/ }).click();
    await seller
      .getByLabel("Сообщение покупателю")
      .fill("Да, сегодня работаем до восьми.");
    await button(seller, "Отправить").click();
    await buyer
      .getByText("Да, сегодня работаем до восьми.", { exact: true })
      .waitFor();
    await button(seller, "Подтвердить выдачу").click();
    await buyer.locator(".chip").filter({ hasText: "Выдан" }).waitFor();
    await capture(buyer, "order");
    await button(seller, "Публикации").click();
    await seller.locator("button.pub-item").filter({ hasText: post }).click();
    assert.deepEqual(
      await seller.locator(".pub-detail strong").allTextContents(),
      ["1", "1", "1", "0"],
    );
    await capture(seller, "publication");
    await button(buyer, "Маркет").click();
    await button(buyer, "Сохранённые (1)").click();
    await buyer.getByRole("button", { name: "Вернуться к товару" }).waitFor();
    await buyer.getByLabel("До, ₽").fill("1000");
    await buyer.getByText(/Подходящих товаров пока нет/).waitFor();
    await button(buyer, "Все товары").click();
    await buyer
      .getByLabel("Получение", { exact: true })
      .selectOption("courier");
    await buyer.getByLabel("До, ₽").fill("1800");
    const second = buyer
      .locator(".product")
      .filter({ hasText: "Кружка «Утро»" });
    await second.getByRole("button").click();
    await buyer.getByLabel(/Курьер/).check();
    await button(buyer, "В корзину").click();
    await buyer.getByLabel("Адрес доставки").fill("Учебный адрес, 12");
    await button(buyer, "Оформить заказ").click();
    const secondTitle = await buyer
      .getByRole("heading", { name: /Заказ №/ })
      .innerText();
    await button(seller, "Заказы").click();
    await seller
      .getByRole("button", {
        name: new RegExp(secondTitle.replace("Заказ ", "")),
      })
      .click();
    await seller
      .getByLabel("Причина отмены")
      .fill("Покупатель перенёс доставку");
    await button(seller, "Отменить заказ").click();
    await buyer.locator(".chip").filter({ hasText: "Отменён" }).waitFor();
    await buyer.getByText(/Покупатель перенёс доставку/).waitFor();
    const data = await seller.evaluate(() =>
      fetch("/api/store").then((r) => r.json()),
    );
    const o = data.orders.find((o) => secondTitle === "Заказ № " + o.id);
    assert.equal(o.surface, "Маркет");
    assert.equal(o.post_id, null);
    assert.equal(data.products.find((x) => x.id === 2).stock, 3);
    assert.equal(
      data.orders.find((o) => title === "Заказ № " + o.id).messages.length,
      2,
    );
    assert.equal(
      await buyer.evaluate(() => document.documentElement.scrollWidth),
      390,
    );
    await button(seller, "Аналитика").click();
    await seller.locator(".origin-line").filter({ hasText: "Маркет" }).click();
    assert.equal(
      await seller.getByLabel("Источник заказа").inputValue(),
      "Маркет",
    );
    assert.equal(await seller.locator(".order").count(), 1);
    await button(seller, "Каталог").click();
    await button(seller, "Добавить товар").click();
    await seller
      .getByLabel("Название", { exact: true })
      .fill("Сахарница с крышкой");
    await seller.getByLabel("Цена, ₽", { exact: true }).fill("2250");
    await seller
      .getByLabel("Фотография товара")
      .setInputFiles(path.join(demo, "public/cup-3.webp"));
    await seller.getByLabel("Адрес самовывоза").fill("Мастерская");
    await seller
      .getByLabel("Текст записи")
      .fill("Сахарницы новой партии уже на полке.");
    await button(seller, "В черновики").click();
    const created = seller
      .locator(".product")
      .filter({ hasText: "Сахарница с крышкой" });
    await created.getByRole("button", { name: "Редактировать" }).click();
    await button(seller, "Опубликовать").click();
    await button(buyer, "Витрина").click();
    const visible = buyer
      .locator(".product")
      .filter({ hasText: "Сахарница с крышкой" });
    await visible.waitFor();
    assert(
      await visible.locator("img").evaluate(async (img) => {
        await img.decode();
        return img.naturalWidth > 0;
      }),
    );
    await button(buyer, "Клипы").click();
    const video = buyer.locator("video");
    await video.evaluate(async (el) => {
      await el.play();
      await new Promise((resolve, reject) => {
        if (el.currentTime > 0.15) return resolve();
        const timeout = setTimeout(() => reject(Error("Клип не проигрывается")), 5000);
        function onTime() {
          if (el.currentTime < .15) return;
          clearTimeout(timeout);
          el.removeEventListener("timeupdate", onTime);
          resolve();
        }
        el.addEventListener("timeupdate", onTime);
      });
      el.pause();
    });
    assert.equal(await video.evaluate(el => Math.round(el.duration)), 9);
    await capture(buyer, "clip");
    const beforeCard = buyer.url();
    const cardTitle = buyer.getByRole("heading", { name: "Кружка «Утро»" });
    await buyer.locator(".clip-tag").click();
    await cardTitle.waitFor();
    await buyer.goBack();
    await buyer.getByRole("heading", { name: "Клипы сообщества" }).waitFor();
    await buyer.goForward();
    await cardTitle.waitFor();
    await button(buyer, "Вернуться к клипу").click();
    await buyer.getByRole("heading", { name: "Клипы сообщества" }).waitFor();
    assert.equal(buyer.url(), beforeCard);
    await buyer.goForward();
    await cardTitle.waitFor();
    await button(buyer, "В корзину").click();
    await button(buyer, "Оформить заказ").click();
    const clipOrder = await buyer.getByRole("heading", { name: /Заказ №/ }).innerText();
    await button(buyer, "Войти как продавец").click();
    // Buyer history cannot reopen buyer-only screens after switching roles.
    await buyer.goBack();
    await buyer.getByText("Требуют внимания", { exact: true }).waitFor();
    await buyer.setViewportSize({ width: 320, height: 740 });
    await assertNavFits(buyer);
    await button(buyer, "Заказы").click();
    await buyer.getByRole("button", { name: new RegExp(clipOrder.replace("Заказ ", "")) }).click();
    await button(buyer, "Подтвердить выдачу").click();
    await buyer.locator(".chip").filter({ hasText: "Выдан" }).waitFor();
    const source = await buyer.evaluate(async () => {
      const store = await fetch("/api/store").then(r => r.json());
      return store.sources.find(s => s.name === "Клипы");
    });
    assert.deepEqual([source.opens, source.orders, source.issued], [1, 1, 1]);
    await button(buyer, "Войти как покупатель").click();
    await assertNavFits(buyer);
    await button(buyer, "Мои заказы").click();
    await buyer.getByRole("button", { name: new RegExp(clipOrder.replace("Заказ ", "")) }).getByText("Выдан").waitFor();
    assert.deepEqual(errors, []);
    console.log(
      "Проверены новый товар с фотографией, публикация, покупка из ленты, сохранение, переписка, выдача, фильтры Маркета, возврат остатка и выдача заказа из клипа при смене роли.",
    );
  } finally {
    if (browser) await browser.close();
    if (server && server.exitCode == null) {
      server.kill();
      await new Promise((r) => server.once("exit", r));
    }
    fs.rmSync(temporary, { recursive: true, force: true });
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
