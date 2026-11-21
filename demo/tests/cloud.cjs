const assert = require("node:assert/strict");
const { randomBytes, randomUUID } = require("node:crypto");
// This opt-in smoke test uses two isolated invitations on the hosted demo.
const endpoint = process.env.JURY_API_URL;
if (!endpoint)
  throw new Error("Set JURY_API_URL to the deployed jury-shop URL");
const room = randomBytes(24).toString("hex"),
  otherRoom = randomBytes(24).toString("hex");
async function call(
  session,
  path,
  method = "GET",
  body,
  r = room,
  expected = 200,
) {
  const resp = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ room: r, session, path, method, body }),
  });
  let data;
  try {
    data = await resp.json();
  } catch {
    throw new Error("HTTP " + resp.status + " non-JSON " + path);
  }
  if (resp.status !== expected)
    console.error(
      "route",
      path,
      "status",
      resp.status,
      "detail",
      data?.detail || data?.message || data?.code,
    );
  assert.equal(resp.status, expected);
  return data;
}
(async () => {
  const login = (role, r = room) =>
    call(null, "session", "POST", { role }, r).then((x) => x.session);
  const [seller, buyer] = await Promise.all([login("seller"), login("buyer")]);
  await call(buyer, "store", "GET", undefined, otherRoom, 401);
  const untouched = await login("seller", otherRoom);
  const newPost = await call(seller, "posts", "POST", {
    product: 2,
    text: "Проверка мастерской",
    request_id: randomUUID(),
  });
  const open = {
    product: 2,
    post_id: null,
    surface: "Клипы",
    request_id: randomUUID(),
  };
  await call(buyer, "opens", "POST", open);
  await call(buyer, "opens", "POST", open);
  const purchase = {
    product: 2,
    quantity: 1,
    method: "pickup",
    quoted_total: 1450,
    surface: "Клипы",
    post_id: null,
    request_id: randomUUID(),
  };
  const [order, replay] = await Promise.all([
    call(buyer, "orders", "POST", purchase),
    call(buyer, "orders", "POST", purchase),
  ]);
  assert.equal(order.id, replay.id);
  await call(seller, "orders", "POST", purchase, room, 403);
  await call(buyer, "orders/" + order.id + "/messages", "POST", {
    text: "Когда забрать?",
    request_id: randomUUID(),
  });
  await call(seller, "orders/" + order.id + "/messages", "POST", {
    text: "Сегодня",
    request_id: randomUUID(),
  });
  await call(seller, "orders/" + order.id, "PATCH", { status: "Выдан" });
  const view = await call(buyer, "store"),
    result = view.orders.find((o) => o.id === order.id);
  assert.equal(result.status, "Выдан");
  assert.equal(result.surface, "Клипы");
  assert.equal(result.messages.length, 2);
  const s = await call(seller, "store"),
    clip = s.sources.find((x) => x.name === "Клипы");
  assert.equal(clip.issued, 1);
  assert.equal(clip.opens, 1);
  const isolated = await call(untouched, "store", "GET", undefined, otherRoom);
  assert.equal(isolated.orders.length, 3);
  const second = await call(buyer, "orders", "POST", {
    ...purchase,
    post_id: newPost.id,
    surface: "Лента",
    request_id: randomUUID(),
  });
  await call(seller, "orders/" + second.id, "PATCH", {
    status: "Отменён",
    reason: "Изменились планы",
  });
  const remaining = await call(seller, "store");
  assert.equal(remaining.products.find((x) => x.id === 2).stock, 2);
  console.log(
    "Public cloud: separate sessions, room isolation, concurrency, replay, messages, issue, clip attribution and cancel verified.",
  );
})().catch((e) => {
  console.error(e.message);
  process.exitCode = 1;
});
