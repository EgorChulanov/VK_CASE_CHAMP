"""Local case prototype. Both demo accounts operate on the same SQLite database."""

import os
import hashlib
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from inventory import (
    CardEdit,
    NewCard,
    initialize_media,
    prepare_photo,
    store_photo,
    product_photo,
)
from publications import (
    Message,
    PostInput,
    Surface,
    Touch,
    check_source,
    migrate,
    open_product,
    publish,
    read_posts,
    sources,
    sync_card,
    write_message,
)


ROOT = Path(__file__).resolve().parent
DB = os.getenv("SHOP_DB", str(ROOT / "shop.sqlite3"))
app = FastAPI(title="Магазин сообщества ВКонтакте")


@contextmanager
def db():
    conn = sqlite3.connect(DB, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def initialize():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, role TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, title TEXT, price INTEGER, stock INTEGER, pickup TEXT, delivery INTEGER, days INTEGER, published INTEGER DEFAULT 0, post TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, product INTEGER REFERENCES products(id), title TEXT, price INTEGER, quantity INTEGER, method TEXT, shipping INTEGER, terms TEXT, status TEXT, request_id TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, order_id INTEGER REFERENCES orders(id), status TEXT, detail TEXT, time TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS saved(product INTEGER PRIMARY KEY REFERENCES products(id));
        """)
        if "version" not in {
            r["name"] for r in c.execute("PRAGMA table_info(products)")
        }:
            c.execute(
                "ALTER TABLE products ADD COLUMN version INTEGER NOT NULL DEFAULT 1"
            )
        if "address" not in {r["name"] for r in c.execute("PRAGMA table_info(orders)")}:
            c.execute("ALTER TABLE orders ADD COLUMN address TEXT NOT NULL DEFAULT ''")
        if not c.execute("SELECT 1 FROM products LIMIT 1").fetchone():
            c.executemany(
                "INSERT INTO products(id,title,price,stock,pickup,delivery,days,published,post) VALUES(?,?,?,?,?,?,?,?,?)",
                [
                    (1, "Кружка «Мел»", 1200, 8, "", 0, 0, 0, ""),
                    (
                        2,
                        "Кружка «Утро»",
                        1450,
                        3,
                        "Мастерская на Покровке",
                        300,
                        2,
                        1,
                        "Три кружки из утренней партии уже на витрине.",
                    ),
                    (
                        3,
                        "Кружка для эспрессо",
                        850,
                        1,
                        "Мастерская на Покровке",
                        250,
                        2,
                        1,
                        "Последняя маленькая кружка этой серии.",
                    ),
                ],
            )
            for i, status in enumerate(["Оформлен", "Выдан", "Отменён"], 1):
                c.execute(
                    "INSERT INTO orders(id,product,title,price,quantity,method,shipping,terms,status,request_id) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (
                        i,
                        2,
                        "Кружка «Утро»",
                        1450,
                        1,
                        "pickup",
                        0,
                        "Мастерская на Покровке",
                        status,
                        f"seed-{i}",
                    ),
                )
                record(c, i, "Оформлен", "Заказ принят магазином")
                if status != "Оформлен":
                    record(
                        c,
                        i,
                        status,
                        "Передан покупателю"
                        if status == "Выдан"
                        else "Покупатель изменил планы",
                    )
        migrate(c)
        initialize_media(c)


def record(c, oid, status, detail):
    c.execute(
        "INSERT INTO events(order_id,status,detail) VALUES(?,?,?)",
        (oid, status, detail),
    )


initialize()


class Login(BaseModel):
    role: Literal["seller", "buyer"]


@app.post("/api/session")
def login(body: Login, response: Response):
    token = secrets.token_urlsafe(32)
    with db() as c:
        c.execute("INSERT INTO sessions VALUES(?,?)", (token, body.role))
    response.set_cookie("shop_session", token, httponly=True, samesite="strict")
    return {"role": body.role}


def role(request: Request):
    with db() as c:
        row = c.execute(
            "SELECT role FROM sessions WHERE token=?",
            (request.cookies.get("shop_session"),),
        ).fetchone()
    if not row:
        raise HTTPException(401, "Выберите роль")
    return row[0]


def require(actual, expected):
    if actual != expected:
        raise HTTPException(403, "Для этой роли действие недоступно")


@app.get("/api/store")
def store(actor=Depends(role)):
    with db() as c:
        products = c.execute(
            "SELECT * FROM products"
            + (" WHERE published=1" if actor == "buyer" else "")
            + " ORDER BY id"
        ).fetchall()
        orders = [dict(r) for r in c.execute("SELECT * FROM orders ORDER BY id DESC")]
        for o in orders:
            o.pop("request_id")
            o["messages"] = [
                dict(m)
                for m in c.execute(
                    "SELECT author,text,created FROM order_messages WHERE order_id=? ORDER BY id",
                    (o["id"],),
                )
            ]

            o["history"] = [
                dict(r)
                for r in c.execute(
                    "SELECT status,detail,time FROM events WHERE order_id=? ORDER BY id",
                    (o["id"],),
                )
            ]
        return {
            "role": actor,
            "posts": read_posts(c, actor == "seller"),
            "sources": sources(c) if actor == "seller" else [],
            "products": [dict(r) for r in products],
            "orders": orders,
            "saved": [r[0] for r in c.execute("SELECT product FROM saved")],
        }


@app.post("/api/posts")
def new_post(body: PostInput, actor=Depends(role)):
    require(actor, "seller")
    with db() as c:
        return {"id": publish(c, body)}


@app.post("/api/opens")
def register_open(body: Touch, actor=Depends(role)):
    require(actor, "buyer")
    with db() as c:
        open_product(c, body)
    return {"ok": True}


@app.post("/api/orders/{oid}/messages")
def add_message(oid: int, body: Message, actor=Depends(role)):
    with db() as c:
        write_message(c, oid, actor, body)
    return {"ok": True}


@app.post("/api/products")
def create_card(body: NewCard, actor=Depends(role)):
    require(actor, "seller")
    values = body.values()
    photo = prepare_photo(body.image_data)
    digest = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        old = c.execute(
            "SELECT product,digest FROM new_cards WHERE request_id=?",
            (body.request_id,),
        ).fetchone()
        if old:
            if old["digest"] != digest:
                raise HTTPException(409, "Этим запросом уже создан другой товар")
            return {"id": old["product"]}
        pid = c.execute(
            "INSERT INTO products(title,price,stock,pickup,delivery,days,post,published) VALUES(?,?,?,?,?,?,?,?)",
            values,
        ).lastrowid
        store_photo(c, pid, photo)
        c.execute("INSERT INTO new_cards VALUES(?,?,?)", (body.request_id, digest, pid))
        if body.published:
            sync_card(c, pid, body.post.strip())
        return {"id": pid}


@app.put("/api/products/{pid}")
def edit(pid: int, body: CardEdit, actor=Depends(role)):
    require(actor, "seller")
    values = body.values()
    photo = prepare_photo(body.image_data)
    with db() as c:
        changed = c.execute(
            "UPDATE products SET title=?,price=?,stock=?,pickup=?,delivery=?,days=?,post=?,published=?,version=version+1 WHERE id=? AND version=?",
            (*values, pid, body.version),
        )
        if not changed.rowcount:
            raise HTTPException(
                409, "Карточка изменилась. Откройте товар заново и проверьте остаток."
            )
        store_photo(c, pid, photo)
        if body.published:
            sync_card(c, pid, body.post.strip())
    return {"ok": True}


@app.get("/api/products/{pid}/photo")
def image(pid: int, actor=Depends(role)):
    with db() as c:
        return product_photo(c, pid, actor == "seller", ROOT / "public")


@app.put("/api/saved/{pid}")
def favorite(pid: int, enabled: bool, actor=Depends(role)):
    require(actor, "buyer")
    with db() as c:
        if not c.execute(
            "SELECT id FROM products WHERE id=? AND published=1", (pid,)
        ).fetchone():
            raise HTTPException(404, "Товар недоступен")
        if enabled:
            c.execute("INSERT OR IGNORE INTO saved VALUES(?)", (pid,))
        else:
            c.execute("DELETE FROM saved WHERE product=?", (pid,))
    return {"ok": True}


class Purchase(BaseModel):
    surface: Surface | None = None
    post_id: int | None = None
    product: int
    quantity: int = Field(ge=1, le=99)
    method: Literal["pickup", "courier"]
    address: str = Field(default="", max_length=220)
    quoted_total: int = Field(ge=0)
    request_id: str = Field(min_length=8, max_length=100)


@app.post("/api/orders")
def purchase(body: Purchase, actor=Depends(role)):
    require(actor, "buyer")
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        old = c.execute(
            "SELECT * FROM orders WHERE request_id=?", (body.request_id,)
        ).fetchone()
        if old:
            expected_address = body.address.strip() if body.method == "courier" else ""
            if (
                old["product"],
                old["quantity"],
                old["method"],
                old["address"],
                old["price"] * old["quantity"] + old["shipping"],
                old["post_id"],
                old["surface"],
            ) != (
                body.product,
                body.quantity,
                body.method,
                expected_address,
                body.quoted_total,
                body.post_id,
                body.surface or "Источник неизвестен",
            ):
                raise HTTPException(409, "Запрос уже использован для другого заказа")
            return {"id": old["id"]}
        p = c.execute(
            "SELECT * FROM products WHERE id=? AND published=1", (body.product,)
        ).fetchone()
        if not p or p["stock"] < body.quantity:
            raise HTTPException(409, "Недостаточно товара в наличии")
        check_source(c, body.product, body.post_id, body.surface)
        pickup = body.method == "pickup"
        if not (p["pickup"].strip() if pickup else p["days"]):
            raise HTTPException(422, "Способ получения недоступен")
        if not pickup and not body.address.strip():
            raise HTTPException(422, "Введите адрес для курьера")
        total = p["price"] * body.quantity + (0 if pickup else p["delivery"])
        if total != body.quoted_total:
            raise HTTPException(
                409, "Цена изменилась. Откройте карточку и проверьте итог."
            )
        terms = p["pickup"] if pickup else f"Курьер за {p['days']} дн."
        oid = c.execute(
            "INSERT INTO orders(product,title,price,quantity,method,shipping,terms,status,request_id,address,post_id,surface) VALUES(?,?,?,?,?,?,?,'Оформлен',?,?,?,?)",
            (
                p["id"],
                p["title"],
                p["price"],
                body.quantity,
                body.method,
                0 if pickup else p["delivery"],
                terms,
                body.request_id,
                "" if pickup else body.address.strip(),
                body.post_id,
                body.surface or "Источник неизвестен",
            ),
        ).lastrowid
        c.execute(
            "UPDATE products SET version=version+1,stock=stock-? WHERE id=?",
            (body.quantity, p["id"]),
        )
        record(c, oid, "Оформлен", terms)
        return {"id": oid}


class Decision(BaseModel):
    status: Literal["Выдан", "Отменён"]
    reason: str = Field(default="", max_length=300)


@app.patch("/api/orders/{oid}")
def decide(oid: int, body: Decision, actor=Depends(role)):
    require(actor, "seller")
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        o = c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        if not o:
            raise HTTPException(404, "Заказ не найден")
        if o["status"] == body.status:
            return {"ok": True}
        if o["status"] != "Оформлен":
            raise HTTPException(409, "Заказ уже завершён")
        if body.status == "Отменён":
            if not body.reason.strip():
                raise HTTPException(422, "Укажите причину отмены")
            c.execute(
                "UPDATE products SET version=version+1,stock=stock+? WHERE id=?",
                (o["quantity"], o["product"]),
            )
        c.execute("UPDATE orders SET status=? WHERE id=?", (body.status, oid))
        record(c, oid, body.status, body.reason.strip() or "Передан покупателю")
    return {"ok": True}


app.mount(
    "/", StaticFiles(directory=ROOT / "dist", html=True, check_dir=False), name="shop"
)
