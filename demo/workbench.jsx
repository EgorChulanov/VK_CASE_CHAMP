import React, { useState } from "react";
import {
  Icon24ArrowRightOutline,
  Icon24StorefrontOutline,
  Icon24MessageOutline,
  Icon24GraphOutline,
  Icon24WriteOutline,
} from "@vkontakte/icons";

const rub = (n) => n.toLocaleString("ru-RU") + " ₽";
const cash = (orders) =>
  orders
    .filter((o) => o.status === "Выдан")
    .reduce((sum, o) => sum + o.price * o.quantity, 0);
const newestQuestion = (order) => order.messages?.at(-1)?.author === "buyer";
export const formatShopTime = (stamp) =>
  new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Moscow",
  }).format(new Date(stamp.replace(" ", "T") + "Z"));

function Head({ title, action, children }) {
  return (
    <div className="panel-head">
      <h2>{title}</h2>
      {action || children}
    </div>
  );
}
function Tile({ icon: Icon, name, value, caption, onClick }) {
  return (
    <button className="summary-tile" onClick={onClick}>
      <Icon />
      <span>{name}</span>
      <strong>{value}</strong>
      <small>{caption}</small>
    </button>
  );
}
function Task({ icon: Icon, title, description, action, onClick }) {
  return (
    <button className="task-row" onClick={onClick}>
      <span className="task-icon">
        <Icon />
      </span>
      <span>
        <b>{title}</b>
        <small>{description}</small>
      </span>
      <span className="task-action">
        {action} <Icon24ArrowRightOutline />
      </span>
    </button>
  );
}

export function Overview({ store, nav, edit, order, dash }) {
  const { orders, products, posts } = store;
  const pending = orders.filter((o) => o.status === "Оформлен");
  const waiting = orders.filter(newestQuestion);
  const draft = products.find((p) => !p.published);
  return (
    <>
      <div className="community-cover">
        <div className="cover-type">Кабинет сообщества</div>
        <h1>Мастерская «Тёплый дом»</h1>
        <p>Керамика ручной работы в Москве</p>
      </div>
      <div className="summary-tiles">
        <Tile
          icon={Icon24StorefrontOutline}
          name="На витрине"
          value={products.filter((p) => p.published).length}
          caption="товаров опубликовано"
          onClick={() => nav("Каталог")}
        />
        <Tile
          icon={Icon24WriteOutline}
          name="Заказы в работе"
          value={pending.length}
          caption="ждут выдачи"
          onClick={() => dash("Оформлен")}
        />
        <Tile
          icon={Icon24GraphOutline}
          name="Выдано товаров на"
          value={rub(cash(orders))}
          caption="за всё время, без доставки"
          onClick={() => dash("Выдан")}
        />
      </div>
      <div className="overview-grid">
        <section className="box">
          <Head title="Требуют внимания" />
          {draft && (
            <Task
              icon={Icon24StorefrontOutline}
              title={draft.title}
              description="Черновик. Проверьте условия получения."
              action="Подготовить товар"
              onClick={() => edit(draft)}
            />
          )}
          {pending.length > 0 && (
            <Task
              icon={Icon24WriteOutline}
              title={"Заказ № " + pending[0].id}
              description={pending[0].title + ", " + pending[0].terms}
              action="Открыть"
              onClick={() => order(pending[0])}
            />
          )}
          {waiting.length > 0 && (
            <Task
              icon={Icon24MessageOutline}
              title="Покупатель ждёт ответа"
              description={waiting[0].messages.at(-1).text}
              action="Ответить"
              onClick={() => order(waiting[0])}
            />
          )}
          {!draft && !pending.length && !waiting.length && (
            <p>Все заказы разобраны. Можно подготовить следующую запись.</p>
          )}
        </section>
        <section className="box">
          <Head title="Записи с товарами" />
          <div className="post-counts">
            <strong>{posts.reduce((n, p) => n + p.opens, 0)}</strong>
            <span>открытий карточек из ленты</span>
          </div>
          <div className="post-counts">
            <strong>{posts.reduce((n, p) => n + p.orders, 0)}</strong>
            <span>заказов после перехода из записи</span>
          </div>
          <button className="text-action" onClick={() => nav("Публикации")}>
            Статистика по записям <Icon24ArrowRightOutline />
          </button>
        </section>
      </div>
    </>
  );
}

export function Posts({ store, publish, busy }) {
  const eligible = store.products.filter((p) => p.published && p.stock > 0);
  const [writing, setWriting] = useState(false),
    [pid, choose] = useState(eligible[0]?.id || 0),
    [copy, change] = useState(""),
    [selected, select] = useState(null),
    [request, setRequest] = useState(() => crypto.randomUUID());
  const post = store.posts.find((p) => p.id === selected);
  function compose(p) {
    choose(p?.product || eligible[0]?.id || 0);
    change(p?.text || "");
    setRequest(crypto.randomUUID());
    setWriting(true);
  }
  async function submit() {
    if (await publish({ product: pid, text: copy, request_id: request })) {
      setWriting(false);
      change("");
    }
  }
  return (
    <>
      <div className="page-intro">
        <div>
          <div className="crumb">Управление сообществом</div>
          <h1>Публикации</h1>
        </div>
        <button
          className="primary-action"
          onClick={() => compose()}
          disabled={!eligible.length}
        >
          Новая запись
        </button>
      </div>
      {writing && (
        <section className="box composer">
          <Head title="Запись с товаром" />
          <label>
            Товар из витрины
            <select
              value={pid}
              onChange={(e) => choose(Number(e.target.value))}
            >
              {eligible.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}, {rub(p.price)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Текст публикации
            <textarea
              maxLength={1500}
              value={copy}
              onChange={(e) => change(e.target.value)}
              placeholder="Расскажите, что появилось в мастерской"
            />
          </label>
          <div className="actions">
            <button
              className="primary-action"
              disabled={
                busy ||
                copy.trim().length < 3 ||
                !eligible.some((p) => p.id === pid)
              }
              onClick={submit}
            >
              Опубликовать запись
            </button>
            <button onClick={() => setWriting(false)}>Закрыть</button>
          </div>
        </section>
      )}
      <section className="box">
        <Head title="Опубликованные записи" />
        <p className="panel-sub">
          Открытия, оформления и выдачи считаются по каждой записи с момента
          публикации.
        </p>
        <div className="pub-list">
          {store.posts.map((p) => (
            <button
              className={"pub-item " + (post?.id === p.id ? "selected" : "")}
              key={p.id}
              onClick={() => select(p.id)}
            >
              <img src={"/api/products/" + p.product + "/photo"} alt="" />
              <span className="pub-text">
                <b>{p.text}</b>
                <small>
                  {p.title}
                  {p.published ? "" : ", товар снят с витрины"}
                </small>
              </span>
              <span className="pub-stat">
                <b>{p.opens}</b>
                <small>открытия</small>
              </span>
              <span className="pub-stat">
                <b>{p.orders}</b>
                <small>заказы</small>
              </span>
            </button>
          ))}
        </div>
      </section>
      {post && (
        <section className="box">
          <Head title={"Результат записи № " + post.id} />
          <p>{post.text}</p>
          <div className="pub-detail">
            {[
              ["Открытия", post.opens],
              ["Оформления", post.orders],
              ["Выдачи", post.issued],
              ["Отмены", post.canceled],
            ].map(([name, n]) => (
              <div key={name}>
                <small>{name}</small>
                <strong>{n}</strong>
              </div>
            ))}
          </div>
          <button
            className="text-action"
            disabled={!eligible.some((p) => p.id === post.product)}
            onClick={() => compose(post)}
          >
            Создать похожую запись
          </button>
        </section>
      )}
    </>
  );
}

export function Feed({ store, open }) {
  const products = new Map(store.products.map((p) => [p.id, p]));
  return (
    <>
      <div className="community-cover compact">
        <div className="cover-type">Сообщество</div>
        <h1>Мастерская «Тёплый дом»</h1>
        <p>Керамика ручной работы в Москве</p>
      </div>
      <h2 className="feed-label">Записи сообщества</h2>
      <div className="post-feed">
        {store.posts.map((post) => {
          const p = products.get(post.product);
          if (!p) return null;
          return (
            <article className="box feed-post" key={post.id}>
              <div className="post-author">
                <span className="round-avatar">Тд</span>
                <span>
                  <b>Тёплый дом</b>
                  <small>{formatShopTime(post.created)}</small>
                </span>
              </div>
              <p>{post.text}</p>
              <img
                className="feed-shot"
                src={"/api/products/" + p.id + "/photo?v=" + p.version}
                alt={p.title}
              />
              <div className="product-attachment">
                <span>
                  <b>{p.title}</b>
                  <small>
                    {rub(p.price)}
                    {p.stock ? " в наличии" : ", распродано"}
                  </small>
                </span>
                <button onClick={() => open(p, "Лента", post.id)}>
                  Открыть товар
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </>
  );
}

export function Market({ store, open, nav }) {
  const [text, query] = useState(""),
    [price, cap] = useState(""),
    [delivery, method] = useState("any"),
    [onlySaved, only] = useState(false);
  const saved = new Set(store.saved);
  const words = text
    .toLowerCase()
    .replace(/[«»]/g, "")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  const eligible = store.products.filter(
    (p) =>
      (p.stock > 0 || (onlySaved && saved.has(p.id))) &&
      (delivery !== "pickup" || p.pickup) &&
      (delivery !== "courier" || p.days > 0),
  );
  const cost = (p) => p.price + (delivery === "courier" ? p.delivery : 0);
  const matches = eligible
    .filter(
      (p) =>
        (!price || cost(p) <= Number(price)) &&
        (!onlySaved || saved.has(p.id)) &&
        words.every((w) => (p.title + " " + p.post).toLowerCase().includes(w)),
    )
    .sort(
      (a, b) =>
        Number(saved.has(b.id)) - Number(saved.has(a.id)) || cost(a) - cost(b),
    );
  return (
    <>
      <div className="page-intro">
        <div>
          <div className="crumb">Покупки ВКонтакте</div>
          <h1>Мой Маркет</h1>
        </div>
      </div>
      <section className="box">
        <Head title="Подобрать товар" />
        <div className="market-filters">
          <label>
            Поиск
            <input
              type="search"
              value={text}
              placeholder="Название или слова из записи"
              onChange={(e) => query(e.target.value)}
            />
          </label>
          <label>
            До, ₽
            <input
              type="number"
              min="0"
              placeholder="Любая сумма"
              value={price}
              onChange={(e) => cap(e.target.value)}
            />
          </label>
          <label>
            Получение
            <select
              aria-label="Получение"
              value={delivery}
              onChange={(e) => method(e.target.value)}
            >
              <option value="any">Любое</option>
              <option value="pickup">Самовывоз</option>
              <option value="courier">Курьер</option>
            </select>
          </label>
        </div>
        <div className="market-toggle">
          <button
            className={!onlySaved ? "active" : ""}
            onClick={() => only(false)}
          >
            Все товары
          </button>
          <button
            className={onlySaved ? "active" : ""}
            onClick={() => only(true)}
          >
            Сохранённые ({store.products.filter((p) => saved.has(p.id)).length})
          </button>
        </div>
        <p className="panel-sub">
          {delivery === "courier" ? "Стоимость включает доставку. " : ""}Сначала
          сохранённые товары, затем по возрастанию цены.
        </p>
        <div className="cards">
          {matches.map((p) => (
            <article className="product" key={p.id}>
              <img
                className="photo"
                src={"/api/products/" + p.id + "/photo?v=" + p.version}
                alt={p.title}
              />
              <h3>{p.title}</h3>
              <b>{rub(cost(p))}</b>
              <small>
                {p.stock === 0
                  ? "Пока нет в наличии"
                  : delivery === "courier"
                    ? "С доставкой за " + p.days + " дн."
                    : p.pickup
                      ? "Есть самовывоз"
                      : "Доступна доставка"}
              </small>
              <button onClick={() => open(p, "Маркет")}>
                {saved.has(p.id) ? "Вернуться к товару" : "Открыть товар"}
              </button>
            </article>
          ))}
        </div>
        {!matches.length && (
          <p>
            Подходящих товаров пока нет. Измените сумму или способ получения.
          </p>
        )}
      </section>
      {store.orders.length > 0 && (
        <section className="hint">
          <div>
            <h2>Знакомая мастерская</h2>
            <p>Тёплый дом</p>
          </div>
          <button onClick={() => nav("Витрина")}>Открыть витрину</button>
        </section>
      )}
    </>
  );
}

export function Inbox({ orders, open }) {
  const [filter, choose] = useState("Все");
  const threads = orders
    .filter((o) => o.messages.length && (filter === "Все" || newestQuestion(o)))
    .sort((a, b) =>
      b.messages.at(-1).created.localeCompare(a.messages.at(-1).created),
    );
  return (
    <section className="box">
      <Head title="Сообщения по заказам" />
      <div className="market-toggle">
        {["Все", "Ждут ответа"].map((f) => (
          <button
            key={f}
            className={f === filter ? "active" : ""}
            onClick={() => choose(f)}
          >
            {f}
          </button>
        ))}
      </div>
      {threads.map((o) => (
        <button key={o.id} className="thread-row" onClick={() => open(o)}>
          <span>
            <b>
              Заказ № {o.id}, {o.title}
            </b>
            <small>{o.messages.at(-1).text}</small>
          </span>
          <b>{newestQuestion(o) ? "Ответить" : "Открыть"}</b>
        </button>
      ))}
      {!threads.length && (
        <p>Здесь появятся вопросы покупателей из карточек заказов.</p>
      )}
    </section>
  );
}

export function Conversation({ order, seller, send, busy }) {
  const [body, set] = useState(""),
    [key, reset] = useState(() => crypto.randomUUID());
  async function submit() {
    if (await send(body, key)) {
      set("");
      reset(crypto.randomUUID());
    }
  }
  return (
    <section className="conversation">
      <h3>Переписка по заказу</h3>
      {order.messages.map((m, i) => (
        <div
          className={"bubble " + (m.author === "seller" ? "from-shop" : "")}
          key={i}
        >
          <b>{m.author === "seller" ? "Мастерская" : "Покупатель"}</b>
          <p>{m.text}</p>
          <small>{formatShopTime(m.created)}</small>
        </div>
      ))}
      <label>
        {seller ? "Сообщение покупателю" : "Вопрос мастерской"}
        <textarea
          rows="2"
          maxLength={600}
          value={body}
          onChange={(e) => set(e.target.value)}
        />
      </label>
      <button
        className="primary-action"
        disabled={busy || !body.trim()}
        onClick={submit}
      >
        Отправить
      </button>
    </section>
  );
}
