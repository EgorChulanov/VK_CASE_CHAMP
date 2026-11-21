import { check, change, view, ShopError } from "./store.js";
import seed from "./seed.json" with { type: "json" };

const service = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const api = Deno.env.get("SUPABASE_URL")! + "/rest/v1";
const encoder = new TextEncoder();
const signingKey = crypto.subtle.importKey(
  "raw",
  encoder.encode(service),
  { name: "HMAC", hash: "SHA-256" },
  false,
  ["sign", "verify"],
);
const hex = (buffer: ArrayBuffer) =>
  Array.from(new Uint8Array(buffer), (v) =>
    v.toString(16).padStart(2, "0"),
  ).join("");
const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "content-type",
  "Cache-Control": "no-store",
};
const json = (data: unknown, status = 200) =>
  Response.json(data, { status, headers: cors });

async function db(
  path: string,
  method = "GET",
  payload?: unknown,
  prefer = "",
) {
  const response = await fetch(api + path, {
    method,
    headers: {
      apikey: service,
      Authorization: "Bearer " + service,
      "Content-Type": "application/json",
      ...(prefer ? { Prefer: prefer } : {}),
    },
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });
  if (!response.ok) {
    console.error("jury database", method, response.status);
    throw new ShopError(
      503,
      "Магазин временно недоступен. Повторите через минуту.",
    );
  }
  return response;
}

async function issue(room: string, role: string) {
  const expires = Date.now() + 7 * 24 * 3600 * 1000;
  const sig = await crypto.subtle.sign(
    "HMAC",
    await signingKey,
    encoder.encode([room, role, expires].join(".")),
  );
  return [role, expires, hex(sig)].join(".");
}
async function actor(room: string, session: unknown) {
  check(
    typeof session === "string" &&
      /^(buyer|seller)\.\d{13}\.[0-9a-f]{64}$/.test(session),
    "Выберите роль",
    401,
  );
  const [role, expires, hash] = (session as string).split(".");
  const signature = Uint8Array.from(hash.match(/../g)!, (pair) =>
    Number.parseInt(pair, 16),
  );
  const valid = await crypto.subtle.verify(
    "HMAC",
    await signingKey,
    signature,
    encoder.encode([room, role, expires].join(".")),
  );
  check(valid && Number(expires) > Date.now(), "Выберите роль", 401);
  return role;
}
Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS")
    return new Response(null, { status: 204, headers: cors });
  try {
    check(req.method === "POST", "Используйте POST", 405);
    check(
      Number(req.headers.get("content-length") || 0) < 3000000,
      "Фотография слишком большая",
      413,
    );
    const input = await req.text();
    check(input.length < 3000000, "Фотография слишком большая", 413);
    let packet;
    try {
      packet = JSON.parse(input);
    } catch {
      throw new ShopError(400, "Не удалось прочитать запрос");
    }
    check(packet && typeof packet === "object", "Не удалось прочитать запрос");
    const { room, session, path, method } = packet;
    check(
      typeof room === "string" && /^[a-f0-9]{48}$/.test(room),
      "Откройте ссылку на магазин",
    );
    check(
      typeof path === "string" &&
        path.length < 120 &&
        typeof method === "string",
      "Неизвестное действие",
    );
    const hash = hex(
      await crypto.subtle.digest("SHA-256", encoder.encode(room)),
    );
    const where = "/jury_rooms?room=eq." + hash;
    if (path === "session" && method === "POST") {
      const role = packet.body?.role;
      check(["seller", "buyer"].includes(role), "Выберите роль");
      await db("/rpc/jury_open_room", "POST", { p_room: hash, p_seed: seed });
      return json({ role, session: await issue(hash, role) });
    }
    const role = await actor(hash, session);
    if (
      path === "store" &&
      method === "GET" &&
      Number.isInteger(packet.known)
    ) {
      const [version] = await (await db(where + "&select=version")).json();
      if (version?.version === packet.known) return json({ same: true });
    }
    for (let attempt = 0; attempt < 6; attempt++) {
      const [row] = await (await db(where + "&select=version,state")).json();
      check(row, "Срок хранения магазина истёк. Выберите роль ещё раз.", 401);
      if (path === "store" && method === "GET")
        return json({ ...view(row.state, role), version: row.version });
      const body = packet.body ?? {};
      check(
        typeof body === "object" && !Array.isArray(body),
        "Некорректный запрос",
      );
      const result = await change(row.state, role, path, method, body);
      check(
        JSON.stringify(row.state).length < 8000000,
        "Магазин заполнен. Уменьшите размер фотографии.",
        413,
      );
      const saved = await (
        await db(
          where + "&version=eq." + row.version + "&select=version",
          "PATCH",
          {
            version: row.version + 1,
            state: row.state,
            touched: new Date().toISOString(),
          },
          "return=representation",
        )
      ).json();
      if (saved.length) return json(result);
    }
    throw new ShopError(
      409,
      "Заказ обновлён в другом окне. Повторите действие.",
    );
  } catch (e) {
    if (e instanceof ShopError) return json({ detail: e.message }, e.status);
    console.error("jury request", e instanceof Error ? e.name : "error");
    return json(
      { detail: "Не удалось обработать запрос. Повторите действие." },
      500,
    );
  }
});
