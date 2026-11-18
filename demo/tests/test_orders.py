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
