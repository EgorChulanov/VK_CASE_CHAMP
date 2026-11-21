"""Publication attribution and buyer questions for the community shop."""

from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field

Surface = Literal["Лента", "Витрина", "Маркет"]


class PostInput(BaseModel):
    product: int
    text: str = Field(min_length=3, max_length=1500)
    request_id: str = Field(min_length=8, max_length=100)


class Touch(BaseModel):
    product: int
    surface: Surface
    post_id: int | None = None
    request_id: str = Field(min_length=8, max_length=100)


class Message(BaseModel):
    text: str = Field(min_length=1, max_length=600)
    request_id: str = Field(min_length=8, max_length=100)


def migrate(c):
    c.executescript("""
        CREATE TABLE IF NOT EXISTS posts(
            id INTEGER PRIMARY KEY, product INTEGER NOT NULL REFERENCES products(id),
            text TEXT NOT NULL, created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            primary_card INTEGER NOT NULL DEFAULT 0, request_id TEXT UNIQUE
        );
        CREATE UNIQUE INDEX IF NOT EXISTS one_card_post ON posts(product) WHERE primary_card=1;
        CREATE TABLE IF NOT EXISTS product_opens(
            id INTEGER PRIMARY KEY, product INTEGER NOT NULL REFERENCES products(id),
            post_id INTEGER REFERENCES posts(id), surface TEXT NOT NULL,
            request_id TEXT NOT NULL UNIQUE, created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS order_messages(
            id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id),
            author TEXT NOT NULL, text TEXT NOT NULL, request_id TEXT NOT NULL UNIQUE,
            created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS opens_by_post ON product_opens(post_id);
        CREATE INDEX IF NOT EXISTS messages_by_order ON order_messages(order_id,id);
    """)
    columns = {row["name"] for row in c.execute("PRAGMA table_info(orders)")}
    if "post_id" not in columns:
        c.execute("ALTER TABLE orders ADD COLUMN post_id INTEGER REFERENCES posts(id)")
    if "surface" not in columns:
        c.execute(
            "ALTER TABLE orders ADD COLUMN surface TEXT NOT NULL DEFAULT 'Источник неизвестен'"
        )
    c.execute("CREATE INDEX IF NOT EXISTS orders_by_post ON orders(post_id)")
    c.execute("""UPDATE events SET detail='Заказ принят магазином' WHERE status='Оформлен'
                 AND detail='Заказ из публикации' AND order_id IN(
                 SELECT id FROM orders WHERE request_id IN ('seed-1','seed-2','seed-3') AND post_id IS NULL)""")
    c.execute("""INSERT OR IGNORE INTO posts(product,text,primary_card)
                 SELECT id,post,1 FROM products WHERE published=1 AND trim(post)!=''""")


def sync_card(c, product, text):
    c.execute(
        """INSERT INTO posts(product,text,primary_card) VALUES(?,?,1)
                 ON CONFLICT(product) WHERE primary_card=1 DO UPDATE SET text=excluded.text""",
        (product, text),
    )


def read_posts(c, seller):
    if seller:
        return [
            dict(row)
            for row in c.execute("""
            SELECT a.*, p.title, p.published, p.stock,
                   (SELECT COUNT(*) FROM product_opens v WHERE v.post_id=a.id) opens,
                   (SELECT COUNT(*) FROM orders o WHERE o.post_id=a.id) orders,
                   (SELECT COUNT(*) FROM orders o WHERE o.post_id=a.id AND o.status='Выдан') issued,
                   (SELECT COUNT(*) FROM orders o WHERE o.post_id=a.id AND o.status='Отменён') canceled
            FROM posts a JOIN products p ON p.id=a.product ORDER BY a.id DESC""")
        ]
    return [
        dict(row)
        for row in c.execute("""
        SELECT a.id,a.product,a.text,a.created,p.title FROM posts a JOIN products p ON p.id=a.product
        WHERE p.published=1 ORDER BY a.id DESC""")
    ]


def sources(c):
    return [
        dict(row)
        for row in c.execute("""
        WITH channels(name) AS (VALUES ('Лента'),('Витрина'),('Маркет'),('Источник неизвестен'))
        SELECT name,
          (SELECT COUNT(*) FROM product_opens WHERE surface=name) AS opens,
          (SELECT COUNT(*) FROM orders WHERE surface=name) AS orders,
          (SELECT COUNT(*) FROM orders WHERE surface=name AND status='Выдан') AS issued
        FROM channels
    """)
    ]


def check_source(c, pid, post_id, surface):
    if surface == "Лента":
        if not c.execute(
            "SELECT 1 FROM posts WHERE id=? AND product=?", (post_id, pid)
        ).fetchone():
            raise HTTPException(422, "Запись не связана с этим товаром")
    elif post_id is not None:
        raise HTTPException(422, "Для этого перехода указывать запись не нужно")


def publish(c, body):
    text = body.text.strip()
    if len(text) < 3:
        raise HTTPException(422, "Добавьте текст публикации")
    c.execute("BEGIN IMMEDIATE")
    existing = c.execute(
        "SELECT id,product,text FROM posts WHERE request_id=?", (body.request_id,)
    ).fetchone()
    if existing:
        if (existing["product"], existing["text"]) != (body.product, text):
            raise HTTPException(409, "Запрос уже использован")
        return existing["id"]
    if not c.execute(
        "SELECT id FROM products WHERE id=? AND published=1 AND stock>0",
        (body.product,),
    ).fetchone():
        raise HTTPException(409, "Выберите товар в наличии на витрине")
    return c.execute(
        "INSERT INTO posts(product,text,request_id) VALUES(?,?,?)",
        (body.product, text, body.request_id),
    ).lastrowid


def open_product(c, touch):
    c.execute("BEGIN IMMEDIATE")
    old = c.execute(
        "SELECT product,post_id,surface FROM product_opens WHERE request_id=?",
        (touch.request_id,),
    ).fetchone()
    if old:
        if tuple(old) != (touch.product, touch.post_id, touch.surface):
            raise HTTPException(
                409, "Этот переход уже зарегистрирован с другим источником"
            )
        return
    if not c.execute(
        "SELECT 1 FROM products WHERE id=? AND published=1", (touch.product,)
    ).fetchone():
        raise HTTPException(404, "Товар недоступен")
    check_source(c, touch.product, touch.post_id, touch.surface)
    c.execute(
        "INSERT INTO product_opens(product,post_id,surface,request_id) VALUES(?,?,?,?)",
        (touch.product, touch.post_id, touch.surface, touch.request_id),
    )


def write_message(c, oid, author, body):
    text = body.text.strip()
    if not text:
        raise HTTPException(422, "Введите сообщение")
    c.execute("BEGIN IMMEDIATE")
    old = c.execute(
        "SELECT order_id,author,text FROM order_messages WHERE request_id=?",
        (body.request_id,),
    ).fetchone()
    if old:
        if tuple(old) != (oid, author, text):
            raise HTTPException(409, "Этот запрос уже относится к другому сообщению")
        return
    if not c.execute("SELECT 1 FROM orders WHERE id=?", (oid,)).fetchone():
        raise HTTPException(404, "Заказ не найден")
    c.execute(
        "INSERT INTO order_messages(order_id,author,text,request_id) VALUES(?,?,?,?)",
        (oid, author, text, body.request_id),
    )
