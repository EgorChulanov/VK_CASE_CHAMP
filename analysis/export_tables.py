"""Create the case workbook with editable assumptions and cached formula results."""

import json
from pathlib import Path

import xlsxwriter

base = Path(__file__).parent


def read(name):
    return json.loads((base / f"{name}.json").read_text())


market = read("market_analysis")
model = read("scenarios")
pilot = read("pilot")
audit = read("dataset_audit")
wb = xlsxwriter.Workbook(base / "VK-Cases.xlsx")
header = wb.add_format(
    {
        "bold": True,
        "font_color": "white",
        "bg_color": "#006AD9",
        "text_wrap": True,
        "valign": "vcenter",
    }
)
integer = wb.add_format({"num_format": "#,##0"})
money = wb.add_format({"num_format": '#,##0 "₽";[Red](#,##0 "₽");0 "₽"'})
percent = wb.add_format({"num_format": "0.0%"})
decimal = wb.add_format({"num_format": "0.00"})
entry = wb.add_format(
    {"font_color": "#0062B8", "bg_color": "#E8F4FF", "num_format": "#,##0"}
)
share = wb.add_format(
    {"font_color": "#0062B8", "bg_color": "#E8F4FF", "num_format": "0%"}
)
note = wb.add_format({"text_wrap": True, "valign": "vcenter", "font_color": "#395368"})


def sheet(name, headers, widths):
    ws = wb.add_worksheet(name)
    ws.hide_gridlines(2)
    ws.freeze_panes(1, 1)
    ws.write_row(0, 0, headers, header)
    ws.set_row(0, 39)
    for i, w in enumerate(widths):
        ws.set_column(i, i, w)
    return ws


def records(name, headers, widths, rows, formats=None):
    ws = sheet(name, headers, widths)
    for i, row in enumerate(rows, 1):
        for j, val in enumerate(row):
            ws.write(i, j, val, (formats or {}).get(j))
    if rows:
        ws.autofilter(0, 0, len(rows), len(headers) - 1)
    return ws


summary = sheet("Решение", ["Что проверяем", "Значение", "Как читать"], [38, 21, 83])
summary_data = [
    (
        "Бизнесы с активными товарами",
        audit["candidate_segments"]["active_product_catalog"]["businesses"],
        "Есть хотя бы один активный товар.",
    ),
    (
        "Выбранный сегмент",
        pilot["businesses"],
        "Есть товар и просмотры товарного контента. Подписчиков больше 1 000 и не больше 100 000.",
    ),
    (
        "Бизнесы с заказом в сегменте",
        pilot["selling"],
        "Хотя бы один заказ через оформление за сентябрь.",
    ),
    (
        "Оформленные заказы сегмента",
        pilot["orders"],
        "На листе бизнесов всего 3 478 оформлений.",
    ),
    (
        "Заказы на бизнес",
        pilot["mean"],
        "Главная метрика эксперимента за 30 дней. В знаменателе все назначенные бизнесы.",
    ),
    ("Разброс заказов на бизнес", pilot["sd"], "Выборочное стандартное отклонение."),
    (
        "Доля сегмента во всех заказах",
        pilot["orders"] / audit["totals"]["orders"],
        "Доля внутри выборки бизнесов.",
    ),
]
for i, (label, value, description) in enumerate(summary_data, 1):
    summary.write(i, 0, label)
    summary.write(
        i, 1, value, percent if i == 7 else decimal if i in (5, 6) else integer
    )
    summary.write(i, 2, description, note)
    summary.set_row(i, 32)
summary.write_url(
    "A10", "internal:'Допущения'!A1", string="Изменить экономические допущения"
)
summary.write_url(
    "A11", "internal:'Экономика'!A1", string="Посмотреть помесячный поток"
)

records(
    "Сегменты",
    [
        "Подписчики",
        "Просмотры контента",
        "Бизнесы",
        "С заказом",
        "Доля с заказом",
        "Заказы",
    ],
    [21, 23, 17, 17, 21, 16],
    [
        (
            r["audience"],
            "Есть" if r["content"] else "Нет",
            r["businesses"],
            r["selling"],
            r["selling_share"],
            r["orders"],
        )
        for r in market["within_audience_segments"]
    ],
    {4: percent},
)
records(
    "Открытия",
    ["Источник", "Открытия VK", "Доля VK", "Открытия партнёра"],
    [34, 23, 18, 24],
    [
        (r["source"], r["vk_opens"], r["vk_share"], r["partner_opens"])
        for r in market["sources"]
    ],
    {1: integer, 2: percent, 3: integer},
)
records(
    "Категории",
    ["Категория", "Открытия VK", "Заказы VK", "Открытия партнёра", "Заказы партнёра"],
    [38, 22, 20, 23, 23],
    [
        (
            r["category"],
            r["opens"],
            r["orders"],
            r["partner_opens"],
            r["partner_orders"],
        )
        for r in market["categories"]
    ],
    {j: integer for j in range(1, 5)},
)

inputs = sheet(
    "Допущения",
    [
        "Сценарий",
        "Доступные магазины",
        "Доля подключения",
        "Доля доп. рекламодателей",
        "Доп. расходы на рекламу, ₽",
        "Активные магазины",
        "Вклад на магазин, ₽",
        "Поток на масштабе, ₽",
    ],
    [20, 18, 18, 21, 22, 18, 18, 24],
)
for i, s in enumerate(model["scenarios"], 1):
    r = i + 1
    inputs.write(i, 0, s["scenario"])
    for j, (key, fmt) in enumerate(
        [
            ("eligible_assumption", entry),
            ("adoption_assumption", share),
            ("incremental_advertiser_share_assumption", share),
            ("incremental_spend_assumption_rub", entry),
        ],
        1,
    ):
        inputs.write(i, j, s[key], fmt)
    inputs.write_formula(i, 5, f"=B{r}*C{r}", integer, s["active"])
    inputs.write_formula(
        i, 6, f"=D{r}*E{r}*$B$8-$B$9", decimal, s["contribution_per_active_rub"]
    )
    inputs.write_formula(i, 7, f"=F{r}*G{r}-$B$10", money, s["net_monthly_steady"])
for row, title, value, fmt in [
    (7, "Стартовые вложения, ₽", model["investment_rub"], entry),
    (8, "Маржа", model["contribution_margin_assumption"], share),
    (9, "Поддержка на магазин, ₽", model["support_per_active_month_rub"], entry),
    (10, "Постоянные расходы, ₽", model["fixed_monthly_rub"], entry),
    (11, "Разгон, мес.", 6, entry),
]:
    inputs.write(row - 1, 0, title)
    inputs.write(row - 1, 1, value, fmt)
inputs.merge_range(
    "A13:H13",
    "Голубые ячейки можно менять. Потоки пересчитаются при открытии книги в Excel.",
    note,
)
inputs.data_validation("B11", {"validate": "integer", "criteria": ">=", "value": 1})
inputs.data_validation(
    "C2:D4", {"validate": "decimal", "criteria": "between", "minimum": 0, "maximum": 1}
)
cash = sheet(
    "Экономика",
    ["Сценарий", "Месяц", "Активные магазины", "Поток за месяц", "Накопленный поток"],
    [20, 15, 24, 23, 24],
)
row = 1
for index, s in enumerate(model["scenarios"], 2):
    for m in s["months"]:
        r = row + 1
        cash.write(row, 0, s["scenario"])
        cash.write(row, 1, m["month_after_launch"])
        cash.write_formula(
            row,
            2,
            f"='Допущения'!F{index}*MIN(B{r}/'Допущения'!$B$11,1)",
            integer,
            m["active"],
        )
        cash.write_formula(
            row,
            3,
            f"=C{r}*'Допущения'!G{index}-'Допущения'!$B$10",
            money,
            m["net_cash"],
        )
        previous = "-'Допущения'!$B$7" if m["month_after_launch"] == 1 else f"E{r - 1}"
        cash.write_formula(row, 4, f"={previous}+D{r}", money, m["cumulative_cash"])
        row += 1
cash.autofilter(0, 0, row - 1, 4)
chart = wb.add_chart({"type": "line"})
for i, s in enumerate(model["scenarios"]):
    start = 1 + i * 24
    chart.add_series(
        {
            "name": s["scenario"],
            "categories": ["Экономика", start, 1, start + 23, 1],
            "values": ["Экономика", start, 4, start + 23, 4],
            "line": {"color": ["#929EAF", "#0077FF", "#198168"][i], "width": 2},
        }
    )
chart.set_title({"name": "Накопленный денежный поток"})
chart.set_y_axis({"name": "Рубли", "num_format": "#,##0"})
chart.set_x_axis({"name": "Месяц после запуска"})
chart.set_legend({"position": "bottom"})
cash.insert_chart("G2", chart)
records(
    "Размер теста",
    ["Рост числа заказов", "Доп. заказы на бизнес", "Бизнесов на группу"],
    [25, 29, 25],
    [(r["lift"], r["absolute_orders"], r["per_arm"]) for r in pilot["sensitivity"]],
    {0: percent, 1: decimal, 2: integer},
)
wb.close()
