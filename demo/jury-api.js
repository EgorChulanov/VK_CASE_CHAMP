// Hosted rooms use the link as an invitation. Keep the room secret out of HTTP referrers.
const cloud = "https://nukxnveftgumbhqqzvgk.supabase.co/functions/v1/jury-shop";
const hosted = /\/prototype\/(?:index\.html)?$/.test(location.pathname);
let room;
let pictures = new Map();
let cachedStore;

function roomKey() {
  if (room) return room;
  const incoming = new URLSearchParams(location.hash.slice(1)).get("room");
  const valid = (v) => /^[0-9a-f]{48}$/.test(v || "");
  const previous = localStorage.getItem("vk-jury-last-room");
  room = valid(incoming)
    ? incoming
    : valid(previous)
      ? previous
      : Array.from(crypto.getRandomValues(new Uint8Array(24)), (b) =>
          b.toString(16).padStart(2, "0"),
        ).join("");
  localStorage.setItem("vk-jury-last-room", room);
  history.replaceState(null, "", juryRoomUrl());
  return room;
}
export function juryRoomUrl() {
  if (!hosted) return "";
  const url = new URL("./", location.href);
  url.hash = "room=" + (room || roomKey());
  return url.href;
}
export function assetUrl(name) {
  return new URL(name.replace(/^\/+/, ""), new URL("./", location.href)).href;
}
export function photoUrl(id, version) {
  if (!hosted)
    return "/api/products/" + id + "/photo" + (version ? "?v=" + version : "");
  return (
    pictures.get(id) ||
    assetUrl(
      [1, 2, 3].includes(id) ? "cup-" + id + ".webp" : "product-default.svg",
    )
  );
}
export function cartKey() {
  return hosted ? "warm-cart-" + roomKey() : "warm-cart";
}
async function contactShop(options, mayRetry) {
  const attempts = mayRetry ? 2 : 1;
  for (let attempt = 1; attempt <= attempts; attempt++) {
    try {
      const response = await fetch(cloud, {
        ...options,
        signal: AbortSignal.timeout(mayRetry ? 12000 : 30000),
      });
      if (attempt === attempts || ![502, 503, 504].includes(response.status)) return response;
    } catch (error) {
      if (attempt === attempts) throw new Error("Не удалось связаться с магазином. Проверьте подключение.", { cause: error });
    }
    await new Promise(resolve => setTimeout(resolve, 450));
  }
}

export async function request(path, method = "GET", body) {
  const headers = { "Content-Type": "application/json" };
  let response;
  if (hosted) {
    const key = roomKey();
    const sessionKey = "vk-jury-role-" + key;
    const session = sessionStorage.getItem(sessionKey);
    if (!session && path !== "session") throw Error("Выберите роль");
    response = await contactShop({
      method: "POST",
      headers,
      cache: "no-store",
      body: JSON.stringify({
        room: key,
        session,
        path,
        method,
        body,
        known:
          path === "store" && cachedStore?.session === session
            ? cachedStore.payload.version
            : undefined,
      }),
    }, path === "session" || method === "GET");
    const payload = await response.json();
    if (!response.ok) {
      if (
        response.status === 401 &&
        sessionStorage.getItem(sessionKey) === session
      )
        sessionStorage.removeItem(sessionKey);
      throw Error(payload.detail || "Не удалось связаться с магазином");
    }
    if (path === "session") sessionStorage.setItem(sessionKey, payload.session);
    if (path === "store") {
      if (
        cachedStore?.session === session &&
        (payload.same || cachedStore.payload.version >= payload.version)
      )
        return cachedStore.payload;
      if (sessionStorage.getItem(sessionKey) !== session)
        throw Error("Роль изменилась");
      cachedStore = { session, payload };
      pictures = new Map(
        Object.entries(payload.pictures || {}).map(([id, url]) => [
          Number(id),
          url,
        ]),
      );
    }
    return payload;
  }
  response = await fetch("/api/" + path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok)
    throw Error(
      typeof data.detail === "string"
        ? data.detail
        : "Проверьте значения полей",
    );
  return data;
}
