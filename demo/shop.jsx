import React, { useEffect, useState } from "react";
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
  Icon24ShoppingCartOutline,
  Icon24MarketOutline,
  Icon24GraphOutline,
  Icon24FavoriteOutline,
  Icon24StorefrontOutline,
} from "@vkontakte/icons";
import "@vkontakte/vkui/dist/vkui.css";
import "./shop.css";

const rub = (n) => new Intl.NumberFormat("ru-RU").format(n) + " ₽";
async function api(path, method = "GET", body) {
  const res = await fetch("/api/" + path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok)
    throw Error(
      typeof data.detail === "string"
        ? data.detail
        : "Проверьте значения полей",
    );
  return data;
}
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
      src={`/cup-${p.id}.webp`}
      alt={p.title}
    />
  );
}
function Edit({ product, commit, busy }) {
  const [p, set] = useState({ ...product });
  const field = (k, v) => set({ ...p, [k]: v });
  return (
    <>
      <div className="crumb">Магазин сообщества › Товары</div>
      <h1>Редактор товара</h1>
      <div className="editgrid">
        <section className="box">
          <Photo p={p} />
          <h2>{p.title}</h2>
          <p>
            {rub(p.price)} · {p.stock} шт. в наличии
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
              disabled={busy}
              onClick={() => commit({ ...p, published: false })}
            >
              В черновики
            </Action>
            <Action
              disabled={busy}
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
  const [store, setStore] = useState(null),
    [loading, load] = useState(true),
    [page, go] = useState("Каталог"),
    [id, select] = useState(1),
    [err, error] = useState(""),
    [busy, lock] = useState(false),
    [filter, filterBy] = useState("Все"),
    [query, search] = useState(""),
    [reason, why] = useState(""),
    [method, choose] = useState("pickup"),
    [qty, count] = useState(1);
  const [cart, setCart] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("warm-cart"));
    } catch {
      return null;
    }
  });
  function basket(v) {
    setCart(v);
    localStorage.setItem("warm-cart", JSON.stringify(v));
  }
  async function refresh() {
    const s = await api("store");
    setStore(s);
    return s;
  }
  useEffect(() => {
    refresh()
      .then((s) => go(s.role === "seller" ? "Каталог" : "Лента"))
      .catch((e) => {
        if (e.message !== "Выберите роль") error(e.message);
      })
      .finally(() => load(false));
  }, []);
  useEffect(() => {
    if (!store) return;
    const timer = setInterval(() => refresh().catch(() => {}), 3500);
    return () => clearInterval(timer);
  }, [store?.role]);
  async function run(fn) {
    if (busy) return;
    lock(true);
    error("");
    try {
      await fn();
    } catch (e) {
      error(e.message);
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
    why("");
  }
  async function login(role) {
    await api("session", "POST", { role });
    await refresh();
    nav(role === "seller" ? "Каталог" : "Лента");
  }
  const seller = store?.role === "seller",
    orders = store?.orders || [],
    products = store?.products || [],
    p = products.find((x) => x.id === id),
    o = orders.find((x) => x.id === id);
  const edit = (x) => {
    select(x.id);
    nav("Редактор");
  };
  const detail = (x) => {
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
        ["Каталог", Icon24StorefrontOutline],
        ["Заказы", Icon24MarketOutline],
        ["Аналитика", Icon24GraphOutline],
      ]
    : [
        ["Лента", Icon24MarketOutline],
        ["Витрина", Icon24StorefrontOutline],
        ["Маркет", Icon24FavoriteOutline],
        ["Корзина", Icon24ShoppingCartOutline],
        ["Мои заказы", Icon24MarketOutline],
      ];
  function dash(status) {
    nav("Заказы");
    filterBy(status);
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
          <p>
            Посмотрите, как запись мастерской становится заказом. Выберите, с
            чьей стороны начать.
          </p>
          <Action onClick={() => run(() => login("seller"))}>
            Войти как продавец
          </Action>{" "}
          <Action secondary onClick={() => run(() => login("buyer"))}>
            Войти как покупатель
          </Action>
        </div>
      </section>
    );
  else if (page === "Редактор" && p)
    content = (
      <Edit
        key={p.id}
        product={p}
        busy={busy}
        commit={(v) =>
          run(async () => {
            await api("products/" + v.id, "PUT", v);
            await refresh();
            nav("Каталог");
          })
        }
      />
    );
  else if (page === "Маркет") {
    const savedProducts = products.filter((product) =>
      store.saved.includes(product.id),
    );
    content = (
      <>
        <div className="crumb">ВКонтакте › Маркет</div>
        <h1>Мой Маркет</h1>
        <section className="box market">
          <h2>Сохранённые товары</h2>
          {savedProducts.length ? (
            <div className="cards">
              {savedProducts.map((product) => (
                <article className="product" key={product.id}>
                  <Photo p={product} />
                  <h3>{product.title}</h3>
                  <p>{rub(product.price)}</p>
                  <Action secondary onClick={() => detail(product)}>
                    Вернуться к товару
                  </Action>
                </article>
              ))}
            </div>
          ) : (
            <p>Нажмите «Сохранить» в карточке, чтобы вернуться к покупке.</p>
          )}
        </section>
        {orders.length > 0 && (
          <section className="hint">
            <div>
              <small>ВЫ УЖЕ ПОКУПАЛИ ЗДЕСЬ</small>
              <h2>Мастерская «Тёплый дом»</h2>
              <p>Ваши заказы и товары знакомого магазина.</p>
            </div>
            <Action secondary onClick={() => nav("Витрина")}>
              Открыть витрину
            </Action>
          </section>
        )}
      </>
    );
  } else if (["Каталог", "Лента", "Витрина"].includes(page)) {
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
          <p>Керамика ручной работы · Москва</p>
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
        <div className="crumb">Тёплый дом › Витрина</div>
        <section className="box detail">
          <Photo p={p} />
          <div>
            <small>МАСТЕРСКАЯ «ТЁПЛЫЙ ДОМ»</small>
            <h1>{p.title}</h1>
            <h2>{rub(p.price)}</h2>
            <Chip>
              {p.stock ? "В наличии · " + p.stock + " шт." : "Распродано"}
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
                Самовывоз бесплатно · {p.pickup}
              </label>
            )}
            {p.days > 0 && (
              <label>
                <input
                  type="radio"
                  checked={method === "courier"}
                  onChange={() => choose("courier")}
                />{" "}
                Курьер · {rub(p.delivery)} · {p.days} дн.
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
                : "Курьер · " + x.days + " дн."}
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
        <h3>История заказа</h3>
        {o.history.map((h, i) => (
          <div className="event" key={i}>
            <b>{h.status}</b> · {h.detail}
            <small>{h.time} UTC</small>
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
      </section>
    );
  } else {
    const subset = orders.filter(
      (x) =>
        (filter === "Все" || filter === x.status) &&
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
          <select value={filter} onChange={(e) => filterBy(e.target.value)}>
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
          <span>Магазин сообщества</span>
          {store && (
            <button
              className="switch"
              onClick={() => run(() => login(seller ? "buyer" : "seller"))}
            >
              {seller ? "Войти как покупатель" : "Войти как продавец"}
            </button>
          )}
        </div>
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
  <ConfigProvider>
    <AdaptivityProvider>
      <AppRoot>
        <Shop />
      </AppRoot>
    </AdaptivityProvider>
  </ConfigProvider>,
);
