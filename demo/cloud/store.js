const channels = ["Лента", "Витрина", "Маркет", "Клипы", "Источник неизвестен"];
const time = () => new Date().toISOString().slice(0, 19).replace("T", " ");
const nextId = (rows) => rows.reduce((n, row) => Math.max(n, row.id), 0) + 1;
export class ShopError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}
export function check(value, message, status = 422) {
  if (!value) throw new ShopError(status, message);
}
function text(value, max, min = 0) {
  check(
    typeof value === "string" &&
      value.length <= max &&
      value.trim().length >= min,
    "Проверьте текст поля",
  );
  return value.trim();
}
function integer(value, min, max) {
  check(
    Number.isInteger(value) && value >= min && value <= max,
    "Проверьте число",
  );
  return value;
}
function requireRole(role, expected) {
  check(role === expected, "Для этой роли действие недоступно", 403);
}
function find(rows, id) {
  const row = rows.find((r) => r.id === id);
  check(row, "Запись не найдена", 404);
  return row;
}
function source(state, body, product) {
  const channel = body.surface || "Источник неизвестен",
    post = body.post_id ?? null;
  check(channels.includes(channel), "Неизвестный источник");
  if (channel === "Лента") {
    check(
      state.posts.some((p) => p.id === post && p.product === product),
      "Запись не связана с этим товаром",
    );
  } else {
    check(post === null, "Для этого канала указывать запись не нужно");
    if (channel === "Клипы")
      check(product === 2, "Этот товар не отмечен в клипе");
  }
  return { surface: channel, post_id: post };
}
function card(body) {
  const fields = {
    title: text(body.title, 100, 1),
    price: integer(body.price, 1, 1000000),
    stock: integer(body.stock, 0, 100000),
    pickup: text(body.pickup, 200),
    days: integer(body.days, 0, 60),
    delivery: integer(body.delivery, 0, 10000),
    post: text(body.post, 2000),
    published: body.published ? 1 : 0,
  };
  check(
    !fields.published || (fields.post && (fields.pickup || fields.days)),
    "Добавьте текст и способ получения",
  );
  return fields;
}
function picture(body) {
  if (body.image_data == null) return null;
  const base64 = body.image_data;
  check(
    typeof base64 === "string" &&
      base64.length <= 2796204 &&
      /^[A-Za-z0-9+/]+={0,2}$/.test(base64),
    "Проверьте фотографию",
  );
  const raw = atob(base64.slice(0, 32));
  const mime = raw.startsWith("\x89PNG\r\n\x1a\n")
    ? "image/png"
    : raw.startsWith("\xff\xd8\xff")
      ? "image/jpeg"
      : raw.startsWith("RIFF") && raw.slice(8, 12) === "WEBP"
        ? "image/webp"
        : "";
  check(mime, "Выберите JPG, PNG или WebP");
  return "data:" + mime + ";base64," + base64;
}
function updatePrimary(state, product) {
  if (!product.published) return;
  const existing = state.posts.find(
    (p) => p.primary_card && p.product === product.id,
  );
  if (existing) existing.text = product.post;
  else
    state.posts.unshift({
      id: nextId(state.posts),
      product: product.id,
      text: product.post,
      primary_card: 1,
      created: time(),
    });
}

export function view(state, role) {
  const seller = role === "seller";
  const products = state.products.filter((p) => seller || p.published);
  const ids = new Set(products.map((p) => p.id));
  const pictures = Object.fromEntries(
    Object.entries(state.pictures).filter(([id]) => ids.has(Number(id))),
  );
  const posts = state.posts
    .filter((p) => ids.has(p.product))
    .map((p) => {
      const product = find(products, p.product);
      if (!seller)
        return {
          id: p.id,
          product: p.product,
          title: product.title,
          text: p.text,
          created: p.created,
        };
      const orders = state.orders.filter((o) => o.post_id === p.id);
      return {
        ...p,
        title: product.title,
        published: product.published,
        stock: product.stock,
        opens: state.opens.filter((o) => o.post_id === p.id).length,
        orders: orders.length,
        issued: orders.filter((o) => o.status === "Выдан").length,
        canceled: orders.filter((o) => o.status === "Отменён").length,
      };
    });
  const sources = seller
    ? channels.map((name) => ({
        name,
        opens: state.opens.filter((x) => x.surface === name).length,
        orders: state.orders.filter((x) => x.surface === name).length,
        issued: state.orders.filter(
          (x) => x.surface === name && x.status === "Выдан",
        ).length,
      }))
    : [];
  return {
    role,
    products,
    posts,
    sources,
    saved: state.saved,
    orders: state.orders,
    pictures,
  };
}

function transact(state, role, path, method, body) {
  const parts = path.split("/");
  if (method === "POST" && path === "posts") {
    requireRole(role, "seller");
    const product = find(state.products, body.product);
    check(
      product.published && product.stock > 0,
      "Выберите товар в наличии на витрине",
      409,
    );
    const id = nextId(state.posts);
    state.posts.unshift({
      id,
      product: product.id,
      text: text(body.text, 1500, 3),
      created: time(),
      primary_card: 0,
    });
    return { id };
  }
  if (method === "POST" && path === "opens") {
    requireRole(role, "buyer");
    const product = find(state.products, body.product);
    check(product.published, "Товар недоступен", 404);
    state.opens.push({
      product: product.id,
      ...source(state, body, product.id),
    });
    return { ok: true };
  }
  if (method === "POST" && path === "products") {
    requireRole(role, "seller");
    const product = { ...card(body), version: 1, id: nextId(state.products) };
    const img = picture(body);
    if (img) state.pictures[product.id] = img;
    state.products.push(product);
    updatePrimary(state, product);
    return { id: product.id };
  }
  if (method === "PUT" && /^products\/\d+$/.test(path)) {
    requireRole(role, "seller");
    const product = find(state.products, Number(parts[1]));
    check(
      product.version === body.version,
      "Карточка изменилась. Откройте её заново.",
      409,
    );
    Object.assign(product, card(body));
    product.version++;
    const img = picture(body);
    if (img) state.pictures[product.id] = img;
    updatePrimary(state, product);
    return { ok: true };
  }
  if (method === "PUT" && /^saved\/\d+\?enabled=(true|false)$/.test(path)) {
    requireRole(role, "buyer");
    const [id, enabled] = parts[1].split("?enabled=");
    const product = find(state.products, Number(id));
    check(product.published, "Товар недоступен", 404);
    state.saved = state.saved.filter((i) => i !== product.id);
    if (enabled === "true") state.saved.push(product.id);
    return { ok: true };
  }
  if (method === "POST" && path === "orders") {
    requireRole(role, "buyer");
    const p = find(state.products, body.product),
      qty = integer(body.quantity, 1, 99);
    check(p.published && p.stock >= qty, "Недостаточно товара в наличии", 409);
    check(
      ["pickup", "courier"].includes(body.method),
      "Выберите способ получения",
    );
    const pickup = body.method === "pickup",
      address = pickup ? "" : text(body.address, 220, 1);
    check(pickup ? p.pickup : p.days, "Способ получения недоступен");
    const shipping = pickup ? 0 : p.delivery;
    check(
      body.quoted_total === p.price * qty + shipping,
      "Цена изменилась. Проверьте итог.",
      409,
    );
    const id = nextId(state.orders);
    state.orders.unshift({
      id,
      product: p.id,
      title: p.title,
      price: p.price,
      quantity: qty,
      method: body.method,
      shipping,
      terms: pickup ? p.pickup : "Курьер за " + p.days + " дн.",
      address,
      status: "Оформлен",
      ...source(state, body, p.id),
      history: [
        { status: "Оформлен", detail: "Заказ принят магазином", time: time() },
      ],
      messages: [],
    });
    p.stock -= qty;
    p.version++;
    return { id };
  }
  if (method === "POST" && /^orders\/\d+\/messages$/.test(path)) {
    const order = find(state.orders, Number(parts[1]));
    order.messages.push({
      author: role,
      text: text(body.text, 600, 1),
      created: time(),
    });
    return { ok: true };
  }
  if (method === "PATCH" && /^orders\/\d+$/.test(path)) {
    requireRole(role, "seller");
    const order = find(state.orders, Number(parts[1]));
    check(["Выдан", "Отменён"].includes(body.status), "Проверьте статус");
    if (order.status === body.status) return { ok: true };
    check(order.status === "Оформлен", "Заказ уже завершён", 409);
    const canceled = body.status === "Отменён";
    const detail = canceled ? text(body.reason, 600, 1) : "Передан покупателю";
    if (canceled) {
      const product = find(state.products, order.product);
      product.stock += order.quantity;
      product.version++;
    }
    order.status = body.status;
    order.history.push({ status: body.status, detail, time: time() });
    return { ok: true };
  }
  throw new ShopError(404, "Такого действия в магазине нет");
}

export async function change(state, role, path, method, body) {
  if (method !== "POST") return transact(state, role, path, method, body);
  const requestId = text(body.request_id, 100, 8);
  const bytes = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(JSON.stringify([role, path, body])),
  );
  const hash = Array.from(new Uint8Array(bytes), (b) =>
    b.toString(16).padStart(2, "0"),
  ).join("");
  const key = role + ":" + requestId;
  if (Object.hasOwn(state.receipts, key)) {
    check(
      state.receipts[key].hash === hash,
      "Этот запрос уже использован",
      409,
    );
    return state.receipts[key].result;
  }
  check(
    Object.keys(state.receipts).length < 3000,
    "У этого магазина закончился лимит записей.",
    409,
  );
  const result = transact(state, role, path, method, body);
  state.receipts[key] = { hash, result };
  return result;
}
