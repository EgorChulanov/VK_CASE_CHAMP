"""Local case prototype. Both demo accounts operate on the same SQLite database."""

import os
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
DB = os.getenv("SHOP_DB", str(ROOT / "shop.sqlite3"))
app = FastAPI(title="Мастерская · ВКонтакте")


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
                record(c, i, "Оформлен", "Заказ из публикации")
                if status != "Оформлен":
                    record(
                        c,
                        i,
                        status,
                        "Передан покупателю"
                        if status == "Выдан"
                        else "Покупатель изменил планы",
                    )


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
            o["history"] = [
                dict(r)
                for r in c.execute(
                    "SELECT status,detail,time FROM events WHERE order_id=? ORDER BY id",
                    (o["id"],),
                )
            ]
        return {
            "role": actor,
            "products": [dict(r) for r in products],
            "orders": orders,
            "saved": [r[0] for r in c.execute("SELECT product FROM saved")],
        }


class Product(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    price: int = Field(gt=0, le=1000000)
    stock: int = Field(ge=0, le=100000)
    pickup: str = Field(max_length=200)
    delivery: int = Field(ge=0, le=10000)
    days: int = Field(ge=0, le=60)
    post: str = Field(max_length=2000)
    published: bool
    version: int = Field(ge=1)


@app.put("/api/products/{pid}")
def edit(pid: int, body: Product, actor=Depends(role)):
    require(actor, "seller")
    if body.published and (
        not body.post.strip() or not (body.pickup.strip() or body.days)
    ):
        raise HTTPException(
            422, "Для публикации добавьте текст записи и способ получения"
        )
    with db() as c:
        values = (
            body.title,
            body.price,
            body.stock,
            body.pickup.strip(),
            body.delivery,
            body.days,
            body.post,
            body.published,
            pid,
            body.version,
        )
        changed = c.execute(
            "UPDATE products SET title=?,price=?,stock=?,pickup=?,delivery=?,days=?,post=?,published=?,version=version+1 WHERE id=? AND version=?",
            values,
        )
        if not changed.rowcount:
            raise HTTPException(
                409, "Карточка изменилась. Откройте товар заново и проверьте остаток."
            )

    return {"ok": True}


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
            if tuple(old[k] for k in ("product", "quantity", "method")) != (
                body.product,
                body.quantity,
                body.method,
            ):
                raise HTTPException(409, "Запрос уже использован")
            return {"id": old["id"]}
        p = c.execute(
            "SELECT * FROM products WHERE id=? AND published=1", (body.product,)
        ).fetchone()
        if not p or p["stock"] < body.quantity:
            raise HTTPException(409, "Недостаточно товара в наличии")
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
            "INSERT INTO orders(product,title,price,quantity,method,shipping,terms,status,request_id,address) VALUES(?,?,?,?,?,?,?,'Оформлен',?,?)",
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
