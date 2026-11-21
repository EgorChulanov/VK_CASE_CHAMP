"""Regression checks for the shared demo accounts and inventory transitions."""

import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

temporary = tempfile.TemporaryDirectory()
os.environ["SHOP_DB"] = str(Path(temporary.name) / "startup.sqlite3")
import server


class ShopTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        setting = patch.object(server, "DB", str(Path(folder.name) / "shop.sqlite3"))
        setting.start()
        self.addCleanup(setting.stop)
        server.initialize()
        self.buyer = TestClient(server.app)
        self.seller = TestClient(server.app)
        for client, role in ((self.buyer, "buyer"), (self.seller, "seller")):
            client.post("/api/session", json={"role": role})

    def product(self, ident):
        return next(
            p
            for p in self.seller.get("/api/store").json()["products"]
            if p["id"] == ident
        )

    def buy(self, key, product=2, **kwargs):
        values = dict(
            product=product,
            quantity=1,
            method="pickup",
            quoted_total=self.product(product)["price"],
            request_id=key,
        )
        return self.buyer.post("/api/orders", json={**values, **kwargs})

    def test_shared_order_retry_cancel_restart(self):
        initial = self.product(2)
        order = self.buy("stable-request").json()["id"]
        self.assertEqual(self.buy("stable-request").json()["id"], order)
        self.assertEqual(self.product(2)["stock"], initial["stock"] - 1)
        self.assertEqual(
            self.seller.put("/api/products/2", json=initial).status_code, 409
        )
        path = f"/api/orders/{order}"
        self.assertEqual(
            self.seller.patch(path, json={"status": "Отменён"}).status_code, 422
        )
        for _ in range(2):
            self.assertEqual(
                self.seller.patch(
                    path, json={"status": "Отменён", "reason": "Изменились планы"}
                ).status_code,
                200,
            )
        server.initialize()
        orders = self.buyer.get("/api/store").json()["orders"]
        record = next(o for o in orders if o["id"] == order)
        self.assertEqual(
            [h["status"] for h in record["history"]], ["Оформлен", "Отменён"]
        )
        self.assertEqual(self.product(2)["stock"], initial["stock"])
        self.assertEqual(
            self.seller.patch(path, json={"status": "Выдан"}).status_code, 409
        )

    def test_concurrent_buyers(self):
        def compete(key):
            return self.buy(key, product=3).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(
                sorted(pool.map(compete, ["request-one", "request-two"])), [200, 409]
            )
        self.assertEqual(self.product(3)["stock"], 0)

    def test_roles_publication_courier_and_price(self):
        draft = self.product(1)
        self.assertEqual(self.buyer.put("/api/products/1", json=draft).status_code, 403)
        self.assertEqual(
            self.seller.put(
                "/api/products/1", json={**draft, "published": True}
            ).status_code,
            422,
        )
        self.assertEqual(
            self.buy("no-address", method="courier", quoted_total=1750).status_code, 422
        )
        self.assertEqual(
            self.buy(
                "wrong-price", method="courier", address="Адрес", quoted_total=1400
            ).status_code,
            409,
        )
        oid = self.buy(
            "courier-order", method="courier", address="Адрес", quoted_total=1750
        ).json()["id"]
        order = next(
            o for o in self.seller.get("/api/store").json()["orders"] if o["id"] == oid
        )
        self.assertEqual(
            (order["shipping"], order["address"], order["price"]), (300, "Адрес", 1450)
        )
        self.assertEqual(
            self.seller.patch(
                f"/api/orders/{oid}", json={"status": "Выдан"}
            ).status_code,
            200,
        )
        self.assertEqual(self.product(2)["stock"], 2)

    def test_independent_posts_event_attribution_and_messages(self):
        post = {
            "product": 2,
            "text": "Другая запись о том же товаре",
            "request_id": "second-post-key",
        }
        self.assertEqual(self.buyer.post("/api/posts", json=post).status_code, 403)
        pid = self.seller.post("/api/posts", json=post).json()["id"]
        self.assertEqual(self.seller.post("/api/posts", json=post).json()["id"], pid)
        self.assertEqual(
            self.seller.post(
                "/api/posts", json={**post, "text": "Изменённая запись"}
            ).status_code,
            409,
        )
        touch = {
            "product": 2,
            "post_id": pid,
            "surface": "Лента",
            "request_id": "touch-test-one",
        }
        for _ in range(2):
            self.assertEqual(self.buyer.post("/api/opens", json=touch).status_code, 200)
        self.assertEqual(
            self.buyer.post(
                "/api/opens", json={**touch, "surface": "Маркет", "post_id": None}
            ).status_code,
            409,
        )
        self.assertEqual(
            self.buy(
                "wrong-source", product=3, surface="Лента", post_id=pid
            ).status_code,
            422,
        )
        oid = self.buy("post-order-one", surface="Лента", post_id=pid).json()["id"]
        self.assertEqual(self.buy("post-order-one", surface="Витрина").status_code, 409)
        route = f"/api/orders/{oid}/messages"
        message = {"text": "Когда можно забрать?", "request_id": "message-key-one"}
        for _ in range(2):
            self.assertEqual(self.buyer.post(route, json=message).status_code, 200)
        self.assertEqual(self.seller.post(route, json=message).status_code, 409)
        self.assertEqual(
            self.seller.post(
                route, json={"text": "После шести", "request_id": "message-key-two"}
            ).status_code,
            200,
        )
        self.seller.patch(f"/api/orders/{oid}", json={"status": "Выдан"})
        store = self.seller.get("/api/store").json()
        actual = next(p for p in store["posts"] if p["id"] == pid)
        self.assertEqual(
            [actual[k] for k in ("opens", "orders", "issued", "canceled")], [1, 1, 1, 0]
        )
        order = next(r for r in store["orders"] if r["id"] == oid)
        self.assertEqual([m["author"] for m in order["messages"]], ["buyer", "seller"])
        self.assertTrue(
            all(
                r["surface"] == "Источник неизвестен"
                for r in store["orders"]
                if r["id"] <= 3
            )
        )

    def test_new_product_upload_and_retry(self):
        import base64
        import io
        from PIL import Image

        out = io.BytesIO()
        Image.new("RGB", (8, 8), "#0077ff").save(out, "PNG")
        photo = base64.b64encode(out.getvalue()).decode()
        body = {
            "title": "Сахарница",
            "price": 2250,
            "stock": 2,
            "pickup": "Мастерская",
            "delivery": 0,
            "days": 0,
            "post": "Новая сахарница из последнего обжига",
            "published": False,
            "request_id": "new-card-id",
            "image_data": photo,
        }
        self.assertEqual(self.buyer.post("/api/products", json=body).status_code, 403)
        self.assertEqual(
            self.seller.post(
                "/api/products", json={**body, "image_data": "bad-photo"}
            ).status_code,
            422,
        )
        pid = self.seller.post("/api/products", json=body).json()["id"]
        self.assertEqual(self.seller.post("/api/products", json=body).json()["id"], pid)
        self.assertEqual(
            self.seller.post(
                "/api/products", json={**body, "title": "Другая карточка"}
            ).status_code,
            409,
        )
        self.assertEqual(self.buyer.get(f"/api/products/{pid}/photo").status_code, 404)
        draft = self.product(pid)
        self.assertEqual(
            self.seller.put(
                f"/api/products/{pid}", json={**draft, "published": True}
            ).status_code,
            200,
        )
        response = self.buyer.get(f"/api/products/{pid}/photo")
        self.assertEqual(response.headers["content-type"], "image/webp")
        self.assertEqual(Image.open(io.BytesIO(response.content)).size, (8, 8))
        self.assertTrue(
            any(
                p["product"] == pid
                for p in self.buyer.get("/api/store").json()["posts"]
            )
        )

    def test_existing_shop_migration(self):
        import sqlite3

        with sqlite3.connect(server.DB) as db:
            db.executescript("""
            DROP TABLE order_messages;
            DROP TABLE product_opens;
            DROP INDEX orders_by_post;
            ALTER TABLE orders DROP COLUMN post_id;
            ALTER TABLE orders DROP COLUMN surface;
            DROP TABLE posts;
            """)
        server.initialize()
        server.initialize()
        store = self.seller.get("/api/store").json()
        self.assertEqual(len(store["posts"]), 2)
        self.assertTrue(
            all(
                o["surface"] == "Источник неизвестен" and o["post_id"] is None
                for o in store["orders"]
            )
        )
