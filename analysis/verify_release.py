"""Independently reconcile the original September workbook, scenario JSON and the jury workbook."""

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, stdev
from openpyxl import load_workbook


def table(sheet):
    rows = sheet.values
    fields = list(next(rows))
    return [dict(zip(fields, row)) for row in rows]


def verify(source, published):
    analysis = Path(__file__).resolve().parent
    audit = json.loads((analysis / "dataset_audit.json").read_text())
    model = json.loads((analysis / "scenarios.json").read_text())
    market = json.loads((analysis / "market_analysis.json").read_text())
    pilot = json.loads((analysis / "pilot.json").read_text())
    workbook = load_workbook(source, read_only=True, data_only=True)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == audit["source_sha256"]
    assert len(workbook.sheetnames) == 7
    shops = table(workbook["Бизнесы"])
    orders = lambda rows: sum(r["Заказы через чекаут"] for r in rows)
    selling = lambda rows: sum(r["Заказы через чекаут"] > 0 for r in rows)
    active = [r for r in shops if r["Число активных товаров в каталоге"] > 0]
    content = [r for r in active if r["Просмотры товарного контента"] > 0]
    target = [r for r in content if 1000 < r["Число подписчиков"] <= 100000]
    assert len({r["ID бизнеса"] for r in shops}) == len(shops) == 9754
    assert (len(active), len(content), len(target)) == (3961, 1117, 493)
    assert (sum(r["Подключён чекаут"] for r in active), selling(active)) == (3641, 285)
    assert (selling(shops), orders(shops), selling(target), orders(target)) == (
        298,
        3478,
        121,
        1869,
    )
    assert sum(r["GMV через чекаут, ₽"] for r in shops) == 9973027
    assert (
        sum(
            r["Заказы через чекаут"]
            for r in sorted(
                shops, key=lambda r: r["Заказы через чекаут"], reverse=True
            )[:10]
        )
        / orders(shops)
        == market["business_order_concentration"]["10"]
    )
    assert [
        sum(r["Заказы через чекаут"] > 0 and not r[k] for r in shops)
        for k in ("Подключён чекаут", "Подключена оплата")
    ] == [14, 268]
    cuts = [
        (lo, hi, views)
        for lo, hi in [(1000, 10000), (10000, 100000)]
        for views in (True, False)
    ]
    counts = []
    for lo, hi, views in cuts:
        group = [
            r
            for r in active
            if lo < r["Число подписчиков"] <= hi
            and (r["Просмотры товарного контента"] > 0) == views
        ]
        counts.append((selling(group), len(group)))
    assert counts == [(84, 396), (66, 1059), (37, 97), (25, 132)]
    counts = [r["Заказы через чекаут"] for r in target]
    assert math.isclose(mean(counts), pilot["mean"]) and math.isclose(
        stdev(counts), pilot["sd"]
    )
    assert (
        math.ceil(
            2 * ((1.959964 + 0.841621) * stdev(counts) / (0.2 * mean(counts))) ** 2
        )
        == 9334
    )
    p0 = selling(target) / len(target)
    p1 = p0 + 0.05
    p = (p0 + p1) / 2
    assert (
        math.ceil(
            (
                (
                    1.959964 * math.sqrt(2 * p * (1 - p))
                    + 0.841621 * math.sqrt(p0 * (1 - p0) + p1 * (1 - p1))
                )
                / 0.05
            )
            ** 2
        )
        == 1238
    )
    sources = table(next(w for w in workbook if "источники" in w.title))
    opens = {
        r["Источник"]: r["Маркет Вконтакте"]
        for r in sources
        if isinstance(r["Маркет Вконтакте"], (int, float))
    }
    for entry in market["sources"]:
        assert math.isclose(
            opens[entry["source"]] / sum(opens.values()), entry["vk_share"]
        )
    categories = table(next(w for w in workbook if "категории" in w.title))
    totals = table(next(w for w in workbook if "итоги" in w.title))
    ordered = next(
        r["Маркет Вконтакте"] for r in totals if r["Метрика"] == "Оформленные заказы"
    )
    assert sum(r["Заказы: Маркет Вконтакте"] for r in categories) - ordered == 21545
    excel = load_workbook(published, data_only=True)
    for i, metric in enumerate(
        (
            "Открытия карточки товара",
            "Оформленные заказы",
            "Доля повторных покупателей (2+ заказа), %",
        ),
        15,
    ):
        official = next(r for r in totals if r["Метрика"] == metric)
        for j, k in [(2, "Маркет Вконтакте"), (3, "Партнёр 1")]:
            assert math.isclose(
                excel["Решение"].cell(i, j).value,
                official[k] / (100 if "%" in metric else 1),
            )
    costs = excel["Допущения"]
    cash = excel["Экономика"]
    for i, scenario in enumerate(model["scenarios"]):
        planned, adopt, share, spend = [
            costs.cell(2 + i, col).value for col in (2, 3, 4, 5)
        ]
        capital, margin, support, fixed, ramp = [
            costs.cell(r, 2).value for r in range(7, 12)
        ]
        balance = -capital
        min_balance = balance
        first_profit = None
        recovery = None
        for month in range(1, 25):
            customers = planned * adopt * min(month / ramp, 1)
            net = customers * (share * spend * margin - support) - fixed
            balance += net
            row = 1 + 24 * i + month
            for col, value, key in [
                (3, customers, "active"),
                (4, net, "net_cash"),
                (5, balance, "cumulative_cash"),
            ]:
                assert math.isclose(cash.cell(row, col).value, value, abs_tol=0.01)
                assert math.isclose(
                    scenario["months"][month - 1][key], value, abs_tol=0.01
                )
            min_balance = min(min_balance, balance)
            if net > 0 and first_profit is None:
                first_profit = month
            if balance >= 0 and recovery is None:
                recovery = month
        assert [cash.cell(21 + i, col).value for col in (8, 9, 10, 11)] == [
            first_profit or "За горизонтом",
            recovery or "За горизонтом",
            -min_balance,
            balance,
        ]
    assert [cash.cell(22, col).value for col in (8, 9, 10, 11)] == [
        3,
        17,
        5195000,
        3015000,
    ]
    assert len(excel.sheetnames) == 7
    formulas = load_workbook(published, data_only=False)
    for row in range(2, 74):
        assert all(
            formulas["Экономика"].cell(row, c).data_type == "f" for c in (3, 4, 5)
        )
    for w in [workbook, excel, formulas]:
        w.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument(
        "--published", type=Path, default=Path(__file__).with_name("VK-Cases.xlsx")
    )
    args = parser.parse_args()
    verify(args.source, args.published)
    print(
        "Сверены исходные группы, агрегаты, размер выборок, три сценария и все 72 помесячных строки Excel."
    )
