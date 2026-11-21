import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ConfigProvider,
  AdaptivityProvider,
  AppRoot,
  Button,
  Spinner,
} from "@vkontakte/vkui";
import {
  Icon32LogoVkColor,
  Icon24HomeOutline,
  Icon24ClipOutline,
  Icon28LinkOutline,
  Icon24Done,
  Icon24WriteOutline,
  Icon24MessageOutline,
  Icon24ShoppingCartOutline,
  Icon24MarketOutline,
  Icon24GraphOutline,
  Icon24FavoriteOutline,
  Icon24StorefrontOutline,
} from "@vkontakte/icons";
import "@vkontakte/vkui/dist/vkui.css";
import "./shop.css";
import { request as api, assetUrl, photoUrl, juryRoomUrl, cartKey } from "./jury-api.js";
import {
  Overview,
  Posts,
  Feed,
  Clips,
  Market,
  Inbox,
  Conversation,
  formatShopTime,
} from "./workbench.jsx";

const rub = (n) => new Intl.NumberFormat("ru-RU").format(n) + " ₽";
function Action({ children, onClick, secondary = false, disabled = false }) {
  return (
    <Button
      size="m"
      mode={secondary ? "secondary" : "primary"}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </Button>
  );
}
function Row({ label, children }) {
  return (
    <div className="row">
      <span>{label}</span>
      <strong>{children}</strong>
    </div>
  );
}
function Chip({ children }) {
  return <span className="chip">{children}</span>;
}
function Photo({ p }) {
  return (
    <img
      className={"photo tone" + p.id}
      src={
        p.image_data
          ? `data:${p.image_type || "image/webp"};base64,${p.image_data}`
          : p.id
            ? photoUrl(p.id, p.version)
            : assetUrl("product-default.svg")
      }
      alt={p.title}
    />
  );
}
function Edit({ product, commit, busy }) {
  const [p, set] = useState({ ...product });
  const [photoError, setPhotoError] = useState("");
  const [reading, setReading] = useState(false);
  const field = (k, v) => set((old) => ({ ...old, [k]: v }));
  async function pickPhoto(file) {
    if (!file) return;
    setPhotoError("");
    if (
      file.size > 2 * 1024 * 1024 ||
      !["image/jpeg", "image/png", "image/webp"].includes(file.type)
    ) {
      setPhotoError("Выберите JPG, PNG или WebP до 2 МБ.");
      return;
    }
    setReading(true);
    try {
      const reader = new FileReader();
      const data = await new Promise((resolve, reject) => {
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(Error("Не удалось прочитать фотографию"));
        reader.readAsDataURL(file);
      });
      set((old) => ({
        ...old,
        image_data: data.split(",")[1],
        image_type: file.type,
      }));
    } catch (error) {
      setPhotoError(error.message);
    } finally {
      setReading(false);
    }
  }
  return (
    <>
      <div className="crumb">Магазин сообщества › Товары</div>
      <h1>{p.id ? "Редактор товара" : "Новый товар"}</h1>
      <div className="editgrid">
        <section className="box">
          <Photo p={p} />
          <h2>{p.title || "Новая карточка"}</h2>
          <label className="photo-choice">
            Фотография товара
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              disabled={reading || busy}
              onChange={(e) => pickPhoto(e.target.files[0])}
            />
          </label>
          {photoError && (
            <p role="alert" className="error">
              {photoError}
            </p>
          )}
          <p>
            {rub(p.price)}, {p.stock} шт. в наличии
          </p>
          <Chip>{p.published ? "В витрине" : "Черновик"}</Chip>
        </section>
        <section className="box">
          <h2>Карточка и получение</h2>
          {[
            ["title", "Название"],
            ["price", "Цена, ₽"],
            ["stock", "Остаток, шт."],
            ["pickup", "Адрес самовывоза"],
            ["delivery", "Стоимость доставки, ₽"],
            ["days", "Срок доставки, дней"],
          ].map(([k, label]) => (
            <label key={k}>
              {label}
              <input
                type={["title", "pickup"].includes(k) ? "text" : "number"}
                value={p[k]}
                onChange={(e) =>
                  field(
                    k,
                    e.target.type === "number"
                      ? Number(e.target.value)
                      : e.target.value,
                  )
                }
              />
            </label>
          ))}
          <label>
            Текст записи
            <textarea
              value={p.post}
              onChange={(e) => field("post", e.target.value)}
            />
          </label>
          <div className="actions">
            <Action
              secondary
              disabled={busy || reading}
              onClick={() => commit({ ...p, published: false })}
            >
              В черновики
            </Action>
            <Action
              disabled={busy || reading}
              onClick={() => commit({ ...p, published: true })}
            >
              Опубликовать
            </Action>
          </div>
        </section>
      </div>
    </>
  );
}
function Shop() {
  const generation = useRef(0);
  const [syncNote, setSyncNote] = useState("");
  const [shared, setShared] = useState(false);
  const [manualLink, setManualLink] = useState("");
  const shareTimer = useRef();
  useEffect(() => () => clearTimeout(shareTimer.current), []);
  async function shareRoom() {
    const url = juryRoomUrl();
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      setShared(true);
      clearTimeout(shareTimer.current);
      shareTimer.current = setTimeout(() => setShared(false), 2300);
    } catch {
      setManualLink(url);
    }
  }
  const [store, setStore] = useState(null),
    [loading, load] = useState(true),
    [page, go] = useState("Обзор"),
    [draft, setDraft] = useState(null),
    [origin, setOrigin] = useState({ surface: "Витрина", post_id: null }),
    [id, select] = useState(1),
    [err, error] = useState(""),
    [busy, lock] = useState(false),
    [filter, filterBy] = useState("Все"),
    [sourceFilter, setSourceFilter] = useState("Все каналы"),
    [query, search] = useState(""),
    [reason, why] = useState(""),
    [method, choose] = useState("pickup"),
    [qty, count] = useState(1);
  const [cart, setCart] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(cartKey()));
    } catch {
      return null;
    }
  });
  function basket(v) {
    setCart(v);
    localStorage.setItem(cartKey(), JSON.stringify(v));
  }
  async function refresh() {
    const ticket = ++generation.current;
    const s = await api("store");
    if (ticket === generation.current) {
      setStore(s);
      setSyncNote("");
    }
    return s;
  }
  useEffect(() => {
    refresh()
      .then((s) => go(s.role === "seller" ? "Обзор" : "Лента"))
      .catch((e) => {
        if (e.message !== "Выберите роль") error(e.message);
      })
      .finally(() => load(false));
  }, []);
  useEffect(() => {
    if (!store) return;
    const timer = setInterval(
      () =>
        refresh().catch(() =>
          setSyncNote("Связь с магазином прервалась. Повторяем подключение."),
        ),
      3500,
    );
    return () => clearInterval(timer);
  }, [store?.role]);
  async function run(fn) {
    if (busy) return;
    lock(true);
    error("");
    try {
      await fn();
      return true;
    } catch (e) {
      error(e.message);
      return false;
    } finally {
      lock(false);
    }
  }
  function nav(v) {
    window.scrollTo(0, 0);
    go(v);
    error("");
    search("");
    filterBy("Все");
    setSourceFilter("Все каналы");
    why("");
  }
  async function login(role) {
    await api("session", "POST", { role });
    await refresh();
    nav(role === "seller" ? "Обзор" : "Лента");
  }
  const seller = store?.role === "seller",
    orders = store?.orders || [],
    products = store?.products || [],
    p = products.find((x) => x.id === id),
    o = orders.find((x) => x.id === id);
  const edit = (x) => {
    setDraft(null);
    select(x.id);
    nav("Редактор");
  };
  const detail = async (x, surface = "Витрина", post_id = null) => {
    try {
      await api("opens", "POST", {
        product: x.id,
        surface,
        post_id,
        request_id: crypto.randomUUID(),
      });
    } catch (e) {
      error(e.message);
      return;
    }
    setOrigin({ surface, post_id });

    select(x.id);
    count(1);
    choose(x.pickup ? "pickup" : "courier");
    nav("Карточка");
  };
  const order = (x) => {
    select(x.id);
    nav("Заказ");
  };
  const tabs = seller
    ? [
        ["Обзор", Icon24HomeOutline],
        ["Каталог", Icon24StorefrontOutline],
        ["Публикации", Icon24WriteOutline],
        ["Сообщения", Icon24MessageOutline],
        ["Заказы", Icon24MarketOutline],
        ["Аналитика", Icon24GraphOutline],
      ]
    : [
        ["Лента", Icon24MarketOutline],
        ["Клипы", Icon24ClipOutline],
        ["Витрина", Icon24StorefrontOutline],
        ["Маркет", Icon24FavoriteOutline],
        ["Корзина", Icon24ShoppingCartOutline],
        ["Мои заказы", Icon24MarketOutline],
      ];
  function dash(status, source = "Все каналы") {
    nav("Заказы");
    filterBy(status);
    setSourceFilter(source);
  }
  let content;
  if (loading) content = <Spinner />;
  else if (!store)
    content = (
      <section className="login">
        <div className="loginphoto" />
        <div>
          <small>МАСТЕРСКАЯ КЕРАМИКИ</small>
          <h1>Тёплый дом</h1>
          <p>Покупатель может выбрать кружку и оформить заказ. В кабинете продавца этот заказ можно подготовить и выдать.</p>
          <div className="role-choices">
            <button className="role-button seller-button" disabled={busy} onClick={() => run(() => login("seller"))}>
              Войти как продавец
            </button>
            <button className="role-button buyer-button" disabled={busy} onClick={() => run(() => login("buyer"))}>
              Войти как покупатель
            </button>
          </div>
        </div>
      </section>
    );
  else if (page === "Редактор" && (p || draft))
    content = (
      <Edit
        key={p?.id || draft.request_id}
        product={p || draft}
        busy={busy}
        commit={(v) =>
          run(async () => {
            if (v.id) await api("products/" + v.id, "PUT", v);
            else await api("products", "POST", v);
            setDraft(null);
            await refresh();
            nav("Каталог");
          })
        }
      />
    );
  else if (page === "Обзор" && seller)
    content = (
      <Overview store={store} nav={nav} edit={edit} order={order} dash={dash} />
    );
  else if (page === "Публикации" && seller)
    content = (
      <Posts
        store={store}
        busy={busy}
        publish={(v) =>
          run(async () => {
            await api("posts", "POST", v);
            await refresh();
          })
        }
      />
    );
  else if (page === "Сообщения" && seller)
    content = <Inbox orders={orders} open={order} />;
  else if (page === "Клипы" && !seller)
    content = <Clips store={store} open={detail} />;
  else if (page === "Лента" && !seller)
    content = <Feed store={store} open={detail} nav={nav} />;
  else if (page === "Маркет" && !seller)
    content = <Market store={store} open={detail} nav={nav} />;
  else if (["Каталог", "Витрина"].includes(page)) {
    const listed = products.filter(
      (x) =>
        x.title.toLowerCase().includes(query.toLowerCase()) &&
        (filter === "Все" ||
          (filter === "Опубликованы" ? x.published : !x.published)),
    );
    content = (
      <>
        <div className="banner">
          <small>{seller ? "УПРАВЛЕНИЕ СООБЩЕСТВОМ" : "СООБЩЕСТВО"}</small>
          <h1>Мастерская «Тёплый дом»</h1>
          <p>Керамика ручной работы в Москве</p>
        </div>
        {seller && products.some((x) => !x.published) && (
          <section className="hint">
            <div>
              <b>Товар ждёт публикации</b>
              <p>
                Проверьте, как покупатель получит заказ, и добавьте товар в
                запись.
              </p>
            </div>
            <Action onClick={() => edit(products.find((x) => !x.published))}>
              Подготовить товар
            </Action>
          </section>
        )}
        <section className="box">
          <div className="heading">
            <h2>{page === "Каталог" ? "Товары сообщества" : page}</h2>
            <span>{listed.length}</span>
            {seller && (
              <button
                className="primary-action add-card"
                onClick={() => {
                  select(null);
                  setDraft({
                    title: "",
                    price: 0,
                    stock: 1,
                    pickup: "",
                    delivery: 0,
                    days: 0,
                    post: "",
                    published: false,
                    request_id: crypto.randomUUID(),
                  });
                  nav("Редактор");
                }}
              >
                Добавить товар
              </button>
            )}
          </div>
          <div className="tools">
            <input
              aria-label="Поиск товара"
              placeholder="Найти товар"
              value={query}
              onChange={(e) => search(e.target.value)}
            />
            {seller && (
              <select
                aria-label="Публикация"
                value={filter}
                onChange={(e) => filterBy(e.target.value)}
              >
                {["Все", "Опубликованы", "Черновики"].map((i) => (
                  <option key={i}>{i}</option>
                ))}
              </select>
            )}
          </div>
          <div className={page === "Лента" ? "feed" : "cards"}>
            {listed.map((x) => (
              <article className="product" key={x.id}>
                {page === "Лента" && (
                  <>
                    <b>Тёплый дом</b>
                    <p>{x.post}</p>
                  </>
                )}
                <Photo p={x} />
                <small>
                  {seller
                    ? x.published
                      ? "В витрине"
                      : "Черновик"
                    : "Ручная работа"}
                </small>
                <h3>{x.title}</h3>
                <div className="price">
                  {rub(x.price)} <span>{x.stock} шт.</span>
                </div>
                <Action
                  secondary
                  onClick={() => (seller ? edit(x) : detail(x))}
                >
                  {seller ? "Редактировать" : "Открыть товар"}
                </Action>
              </article>
            ))}
          </div>
          {!listed.length && <p>Здесь пока нет товаров.</p>}
        </section>
      </>
    );
  } else if (page === "Карточка" && p) {
    const saved = store.saved.includes(p.id);
    content = (
      <>
        <div className="crumb">Тёплый дом › {origin.surface}</div>
        <section className="box detail">
          <Photo p={p} />
          <div>
            <small>МАСТЕРСКАЯ «ТЁПЛЫЙ ДОМ»</small>
            <h1>{p.title}</h1>
            <h2>{rub(p.price)}</h2>
            <Chip>
              {p.stock ? "В наличии / " + p.stock + " шт." : "Распродано"}
            </Chip>
            <p>
              {
                {
                  1: "Молочная глазурь и округлая ручка. Каждую кружку мастер покрывает вручную.",
                  2: "Голубая глазурь и открытый край тёплой глины. Широкая ручка удобно лежит в руке.",
                  3: "Небольшая чашка для эспрессо с тёмной глянцевой глазурью.",
                }[p.id]
              }
            </p>
            <h3>Получение</h3>
            {p.pickup && (
              <label>
                <input
                  type="radio"
                  checked={method === "pickup"}
                  onChange={() => choose("pickup")}
                />{" "}
                Самовывоз бесплатно / {p.pickup}
              </label>
            )}
            {p.days > 0 && (
              <label>
                <input
                  type="radio"
                  checked={method === "courier"}
                  onChange={() => choose("courier")}
                />{" "}
                Курьер / {rub(p.delivery)} / {p.days} дн.
              </label>
            )}
            <label>
              Количество
              <input
                type="number"
                min="1"
                max={p.stock}
                value={qty}
                onChange={(e) => count(Number(e.target.value))}
              />
            </label>
            <div className="actions">
              <Action
                disabled={qty < 1 || qty > p.stock || !Number.isInteger(qty)}
                onClick={() => {
                  basket({
                    ...origin,
                    product: p.id,
                    quantity: qty,
                    method,
                    quoted_total:
                      p.price * qty + (method === "pickup" ? 0 : p.delivery),
                    address: "",
                    request_id: crypto.randomUUID(),
                  });
                  nav("Корзина");
                }}
              >
                В корзину
              </Action>
              <Action
                secondary
                onClick={() =>
                  run(async () => {
                    await api("saved/" + p.id + "?enabled=" + !saved, "PUT");
                    await refresh();
                  })
                }
              >
                {saved ? "В сохранённых" : "Сохранить"}
              </Action>
            </div>
          </div>
        </section>
      </>
    );
  } else if (page === "Корзина") {
    const x = products.find((x) => x.id === cart?.product);
    content = (
      <section className="box">
        <h1>Корзина</h1>
        {x ? (
          <>
            <Row label={x.title}>
              {cart.quantity} × {rub(x.price)}
            </Row>
            <Row label="Получение">
              {cart.method === "pickup"
                ? x.pickup
                : "Курьер / " + x.days + " дн."}
            </Row>
            <Row label="Доставка">
              {rub(cart.method === "pickup" ? 0 : x.delivery)}
            </Row>
            {cart.method === "courier" && (
              <label>
                Адрес доставки
                <input
                  autoComplete="street-address"
                  value={cart.address || ""}
                  onChange={(e) => basket({ ...cart, address: e.target.value })}
                />
              </label>
            )}
            <Row label="Итого">{rub(cart.quoted_total)}</Row>
            <div className="actions">
              <Action
                disabled={
                  busy || (cart.method === "courier" && !cart.address?.trim())
                }
                onClick={() =>
                  run(async () => {
                    let n = await api("orders", "POST", cart);
                    basket(null);
                    await refresh();
                    order(n);
                  })
                }
              >
                Оформить заказ
              </Action>
              <Action secondary onClick={() => basket(null)}>
                Удалить
              </Action>
            </div>
          </>
        ) : (
          <p>Добавьте товар из витрины.</p>
        )}
      </section>
    );
  } else if (page === "Аналитика") {
    content = (
      <section className="box">
        <div className="crumb">Магазин сообщества</div>
        <h1>Аналитика заказов</h1>
        <p>
          Все заказы этой мастерской. Выберите показатель, чтобы посмотреть
          состав.
        </p>
        <div className="cards">
          {["Все", "Выдан", "Отменён"].map((s) => (
            <button key={s} className="kpi" onClick={() => dash(s)}>
              <span>
                {s === "Все"
                  ? "Оформления"
                  : s === "Выдан"
                    ? "Выдачи"
                    : "Отмены"}
              </span>
              <b>
                {orders.filter((x) => s === "Все" || x.status === s).length}
              </b>
            </button>
          ))}
        </div>
        <h3>Исход заказов</h3>
        <div className="statuschart">
          {["Оформлен", "Выдан", "Отменён"].map((status, i) => {
            let n = orders.filter((x) => x.status === status).length;
            return (
              <button key={status} onClick={() => dash(status)}>
                <span>
                  {status === "Оформлен"
                    ? "Ждут выдачи"
                    : status === "Выдан"
                      ? "Выданы"
                      : "Отменены"}
                </span>
                <i>
                  <u
                    style={{
                      width:
                        (orders.length ? (n / orders.length) * 100 : 0) + "%",
                      background: ["#0077ff", "#24936c", "#ad6554"][i],
                    }}
                  />
                </i>
                <b>{n}</b>
              </button>
            );
          })}
        </div>
        <section className="origin-report">
          <h3>Откуда пришли заказы</h3>
          <div className="origin-labels">
            <span>Точка входа</span>
            <span>Открытия</span>
            <span>Заказы</span>
            <span>Выдачи</span>
          </div>
          {store.sources.map((source) => (
            <button
              key={source.name}
              className="origin-line"
              onClick={() => dash("Все", source.name)}
            >
              <b>{source.name}</b>
              <span>
                {source.name === "Источник неизвестен"
                  ? "Нет данных"
                  : source.opens}
              </span>
              <b>{source.orders}</b>
              <span>{source.issued}</span>
            </button>
          ))}
        </section>
        <Row label="Стоимость выданных товаров">
          {rub(
            orders
              .filter((x) => x.status === "Выдан")
              .reduce((a, x) => a + x.price * x.quantity, 0),
          )}
        </Row>
      </section>
    );
  } else if (page === "Заказ" && o) {
    content = (
      <section className="box">
        <div className="crumb">Тёплый дом › Заказы</div>
        <h1>Заказ № {o.id}</h1>
        <Chip>{o.status}</Chip>
        <Row label={o.title}>
          {o.quantity} × {rub(o.price)}
        </Row>
        <Row label="Получение">{o.terms}</Row>
        {o.address && <Row label="Адрес доставки">{o.address}</Row>}
        <Row label="Доставка">{rub(o.shipping)}</Row>
        <Row label="Итого">{rub(o.price * o.quantity + o.shipping)}</Row>
        <Row label="Источник заказа">
          {o.surface}
          {o.post_id ? " (запись № " + o.post_id + ")" : ""}
        </Row>
        <h3>История заказа</h3>
        {o.history.map((h, i) => (
          <div className="event" key={i}>
            <b>{h.status}</b> <span>{h.detail}</span>
            <small>{formatShopTime(h.time)} мск</small>
          </div>
        ))}
        {seller && o.status === "Оформлен" && (
          <div className="decision">
            <Action
              disabled={busy}
              onClick={() =>
                run(async () => {
                  await api("orders/" + id, "PATCH", { status: "Выдан" });
                  await refresh();
                })
              }
            >
              Подтвердить выдачу
            </Action>
            <label>
              Причина отмены
              <input value={reason} onChange={(e) => why(e.target.value)} />
            </label>
            <Action
              secondary
              disabled={!reason.trim() || busy}
              onClick={() =>
                run(async () => {
                  await api("orders/" + id, "PATCH", {
                    status: "Отменён",
                    reason,
                  });
                  await refresh();
                })
              }
            >
              Отменить заказ
            </Action>
          </div>
        )}
        <Conversation
          key={o.id}
          order={o}
          seller={seller}
          busy={busy}
          send={(text, request_id) =>
            run(async () => {
              await api("orders/" + o.id + "/messages", "POST", {
                text,
                request_id,
              });
              await refresh();
            })
          }
        />
      </section>
    );
  } else {
    const subset = orders.filter(
      (x) =>
        (filter === "Все" || filter === x.status) &&
        (sourceFilter === "Все каналы" || sourceFilter === x.surface) &&
        (x.title + " " + x.id).toLowerCase().includes(query.toLowerCase()),
    );
    content = (
      <section className="box">
        <h1>{seller ? "Заказы сообщества" : "Мои заказы"}</h1>
        <div className="tools">
          <input
            placeholder="Номер или товар"
            value={query}
            onChange={(e) => search(e.target.value)}
          />
          {seller && (
            <select
              aria-label="Источник заказа"
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
            >
              {["Все каналы", ...store.sources.map((row) => row.name)].map(
                (source) => (
                  <option key={source}>{source}</option>
                ),
              )}
            </select>
          )}
          <select
            aria-label="Статус заказа"
            value={filter}
            onChange={(e) => filterBy(e.target.value)}
          >
            {["Все", "Оформлен", "Выдан", "Отменён"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </div>
        {subset.map((x) => (
          <button className="order" key={x.id} onClick={() => order(x)}>
            <b>№ {x.id}</b>
            <span>{x.title}</span>
            <Chip>{x.status}</Chip>
            <b>{rub(x.price * x.quantity + x.shipping)}</b>
          </button>
        ))}
        {!subset.length && <p>Заказов с такими условиями нет.</p>}
      </section>
    );
  }
  return (
    <>
      <header>
        <div className="headinner">
          <Icon32LogoVkColor />
          <b>ВКонтакте</b>
          <span>{seller ? "Для бизнеса" : "Магазин сообщества"}</span>
          {store && (
            <div className="shop-utilities">
              {juryRoomUrl() && (
                <button className="share-shop" onClick={shareRoom} aria-label={shared ? "Ссылка на магазин скопирована" : "Скопировать ссылку на магазин"} title="Скопировать ссылку на этот магазин">
                  {shared ? <Icon24Done width={18} height={18} /> : <Icon28LinkOutline width={18} height={18} />}
                  <span aria-live="polite">{shared ? "Скопировано" : "Ссылка на магазин"}</span>
                </button>
              )}
            <button
              className="switch"
              title="Сменить роль в этом магазине"
              onClick={() => run(() => login(seller ? "buyer" : "seller"))}
            >
              {seller ? "Войти как покупатель" : "Войти как продавец"}
            </button>
            </div>
          )}
        </div>
        {manualLink && <div className="manual-share">
          <label>Ссылка на этот магазин <input value={manualLink} readOnly onFocus={(e) => e.currentTarget.select()} autoFocus /></label>
          <button onClick={() => setManualLink("")}>Закрыть</button>
        </div>}
      </header>
      <div className={"layout " + (!store ? "solo" : "")}>
        {store && (
          <nav>
            <div className="avatar">Тд</div>
            <h3>Тёплый дом</h3>
            <small>{seller ? "Кабинет продавца" : "Магазин"}</small>
            {tabs.map(([label, Icon]) => (
              <button
                key={label}
                className={page === label ? "active" : ""}
                onClick={() => nav(label)}
              >
                <Icon />
                {label}
              </button>
            ))}
          </nav>
        )}
        <main>
          {syncNote && (
            <p className="sync-note" role="status">
              {syncNote}
            </p>
          )}
          {err && (
            <p role="alert" className="error">
              {err}
            </p>
          )}
          {content}
        </main>
      </div>
    </>
  );
}
createRoot(document.getElementById("root")).render(
  <ConfigProvider colorScheme="light">
    <AdaptivityProvider>
      <AppRoot>
        <Shop />
      </AppRoot>
    </AdaptivityProvider>
  </ConfigProvider>,
);
