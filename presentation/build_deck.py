"""Build the jury deck and expanded journey from the same analysis and product path."""

import json
from html import escape
from pathlib import Path
from journey import stages, render_page

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
PUBLIC = "https://egorchulanov.github.io/vk-case-2026/"
model, market, pilot, audit = [
    json.loads((ROOT / "analysis" / (f + ".json")).read_text())
    for f in ("scenarios", "market_analysis", "pilot", "dataset_audit")
]
blue, navy, grey = "#0077ff", "#225484", "#9fb3c9"
tabs = [
    ("Команда", 2),
    ("Решение", 3),
    ("Рынок", 4),
    ("Аудитория", 5),
    ("Продукт", 6),
    ("Запуск", 8),
    ("Приложение", 9),
]
case = "Развитие элементов социальной коммерции для бизнес-сообществ во ВКонтакте"
pages = []


def img(name, cls="", alt=""):
    return f'<img src="assets/{name}" class="{cls}" alt="{escape(alt)}">'


def slide(tab, title, content):
    n = len(pages) + 1
    links = "".join(
        f'<a href="#p{i}" class="{"on" if t == tab else ""}">{t}</a>' for t, i in tabs
    )
    pages.append(
        f'<section id="p{n}" class="slide"><nav class="top" aria-label="Разделы">{img("icon-vk.svg", alt="ВКонтакте")}<div class="tabs">{links}</div><span class="number">{n:02d} / 14</span></nav><header class="heading"><h1>{title}</h1></header><main>{content}</main></section>'
    )


def grid(*cells, style="three"):
    return f'<div class="grid {style}">' + "".join(cells) + "</div>"


def col(icon, title, body):
    return (
        '<article><h2 class="sectiontitle">'
        + img(f"icon-{icon}.svg")
        + title
        + "</h2>"
        + body
        + "</article>"
    )


def item(title, body):
    return f'<div class="entry"><h3>{title}</h3><p>{body}</p></div>'


def note(title, body, kind="tint"):
    return f'<aside class="{kind}"><h3>{title}</h3><p>{body}</p></aside>'


def stat(n, text):
    return f'<div class="metric">{n}</div><p class="sub">{text}</p>'


def bar(title, v, label, limit=100, color=blue):
    return f'<div class="bar"><div class="barline"><span>{title}</span><b>{label}</b></div><div class="rail"><i style="width:{v / limit * 100:.3f}%;background:{color}"></i></div></div>'


def stem(parent, leaves):
    return (
        '<div class="branch"><strong class="rootnode">'
        + parent
        + '</strong><div class="limbs">'
        + "".join(f'<div class="bnode"><b>{t}</b>{v}</div>' for t, v in leaves)
        + "</div></div>"
    )


def qr(kind, path, title, text):
    return f'<a class="scan" href="{PUBLIC}{path}">{img("qr-" + kind + ".svg", alt=title)}<div><b>{title} ↗</b><span>{text}</span></div></a>'


def n(v):
    return f"{v:,.0f}".replace(",", " ")


def comma(v, d=1):
    return f"{v:.{d}f}".replace(".", ",")


def chart():
    base = model["scenarios"][1]
    cash = [-model["investment_rub"]] + [r["cumulative_cash"] for r in base["months"]]
    x = lambda i: 47 + 17.1 * i
    y = lambda v: 13 + (4 - v / 1_000_000) * 17.8
    gridlines = "".join(
        f'<path d="M47 {y(v * 1e6)}H459" class="{"zero" if v == 0 else "gridline"}"/><text x="34" y="{y(v * 1e6) + 5}" text-anchor="end">{v if v <= 0 else "+" + str(v)}</text>'
        for v in (-6, -4, -2, 0, 2, 4)
    )
    ticks = "".join(
        f'<text x="{x(i)}" y="212" text-anchor="middle">{i}</text>'
        for i in (0, 2, 6, 12, 17, 24)
    )
    points = " ".join(f"{x(i):.1f},{y(c):.1f}" for i, c in enumerate(cash))
    dots = "".join(
        f'<circle cx="{x(i)}" cy="{y(cash[i])}" r="4.5" fill="{c}" stroke="white" stroke-width="2"/>'
        for i, c in [(2, navy), (17, "#08785e"), (24, blue)]
    )
    return f'<svg class="cashplot" viewBox="0 0 482 218" role="img" aria-label="Накопленный поток в миллионах рублей, от минус 4,8 при старте до плюс 3,015 к концу 24-го месяца">{gridlines}{ticks}<path d="M{x(17)} {y(0)}V192" class="guide"/><polyline points="{points}" fill="none" stroke="#0077ff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>{dots}</svg>'


def source(title, body, url=None):
    tag = "a" if url else "div"
    href = f' href="{url}"' if url else ""
    return f'<{tag} class="source"{href}><b>{title}{" ↗" if url else ""}</b><p>{body}</p></{tag}>'


pages.append(
    '<section id="p1" class="slide cover"><div class="coverleft">'
    + img("logos.png", "wordmarks", "VK Education и ВКонтакте")
    + '<div class="event">VK CASE CHAMP 2026</div><h1>'
    + case
    + '</h1><div class="covertail"><b>Digital Cat$</b><span>Москва, 2026</span></div></div>'
    + img("shapes.jpg", "coverart")
    + "</section>"
)

team = [
    (
        "Егор Чуланов",
        "Продукт и прототип",
        "Кабинет продавца и оформление заказа из клипа.",
        "team-egor.webp",
        "laptop",
    ),
    (
        "Екатерина Макаренко",
        "Исследование и путь покупателя",
        "Каналы продаж, выбор товара и условия получения.",
        "team-kate.webp",
        "compass",
    ),
    (
        "Максим Ширяев",
        "Данные и эксперимент",
        "Отбор сообществ, метрики заказов и план эксперимента.",
        "team-maxim.webp",
        "graph",
    ),
    (
        "Анфиса Опарина",
        "Экономика и запуск",
        "Бюджет пилота, денежный поток и срок окупаемости.",
        "team-anfisa.webp",
        "wallet",
    ),
]


def team_card(member):
    name, role, desc, photo, icon = member
    return (
        '<article class="person"><div class="portrait-stage">'
        + img(photo, "portrait", name)
        + f'</div><h2><span>{name}</span></h2><h3>'
        + img(f"vk-icons/{icon}_outline_24.svg")
        + f'{role}</h3><p>{desc}</p></article>'
    )


slide(
    "Команда",
    "Команда Digital Cat$",
    '<div class="people">'
    + "".join(team_card(t) for t in team)
    + "</div>",
)

active = audit["candidate_segments"]["active_product_catalog"]
slide(
    "Решение",
    "Предложение для ВКонтакте",
    grid(
        col(
            "chart",
            "Выводы из анализа",
            stat(
                n(active["businesses"]),
                "бизнес с активным товаром в сентябрьской выборке кейса",
            )
            + bar(
                "Подключили оформление",
                100 * active["checkout_enabled"] / active["businesses"],
                "3 641",
            )
            + bar(
                "Получили заказ",
                100 * active["with_orders"] / active["businesses"],
                "285",
                color=navy,
            )
            + item(
                "Первые 493 сообщества",
                "Уже публикуют товары, получают просмотры и имеют от 1 001 до 100 000 подписчиков. В сентябре 121 магазин получил хотя бы один заказ.",
            )
            + stat("1 869", "заказов в этих сообществах за сентябрь"),
        ),
        col(
            "post",
            "Инициативы",
            stem(
                "Магазин сообщества",
                [
                    (
                        "Карточка до публикации",
                        "Продавец указывает способ получения. Для VK считаем магазины, впервые включившие оформление.",
                    ),
                    (
                        "Записи и клипы",
                        "Продавец видит заказы из каждой записи. Для VK важен прирост заказов по всем каналам.",
                    ),
                    (
                        "Общение по заказу",
                        "Переписка хранится в заказе. Продавец отмечает выдачу, VK видит долю выданных заказов.",
                    ),
                ],
            )
            + note(
                "Роль Маркета",
                "Вернуть покупателя к сохранённой вещи с актуальной ценой и наличием.",
            ),
        ),
        col(
            "check",
            "Ожидаемый результат",
            stat(
                comma(pilot["mean"], 2),
                "заказа на бизнес в выбранном сегменте за сентябрь",
            )
            + bar("Исходное среднее", pilot["mean"], "3,79", 5, navy)
            + bar("Цель эксперимента", pilot["mean"] * 1.2, "4,55", 5)
            + item(
                "Цель на 30 дней",
                "Прирост на 0,76 заказа на бизнес. В расчёт входят все участники теста, в том числе магазины с нулём заказов.",
            )
            + note(
                "Магазины без заказов",
                "У 372 сообществ в сентябре не было заказов. Измерим, какая доля из них получит хотя бы один заказ за 30 дней.",
                "mint",
            ),
        ),
    ),
)

srcs = market["sources"]
labels = ["Другое", "Витрина магазина", "Лента", "Клипы", "Поиск", "Главная Маркета"]
slide(
    "Рынок",
    "Каналы продаж и роль Маркета",
    grid(
        col(
            "chart",
            "Откуда открывают товары",
            '<p class="sub">Доли открытий карточек внутри VK за сентябрь 2026 года</p>'
            + "".join(
                bar(
                    l,
                    r["vk_share"] * 100,
                    comma(r["vk_share"] * 100, 2 if i == 5 else 1) + "%",
                    42,
                    c,
                )
                for i, (l, r, c) in enumerate(
                    zip(labels, srcs, [grey, blue, navy, navy, grey, blue])
                )
            )
            + stat("18,6%", "доля ленты и клипов среди открытий карточек"),
        ),
        col(
            "shop",
            "Как начинается покупка",
            item(
                "Ozon",
                "Покупатель ищет товар и сравнивает предложения. Витрина собирает ассортимент продавца.",
            )
            + item(
                "Авито",
                "Из объявления покупатель может написать продавцу и уточнить условия покупки в чате.",
            )
            + item(
                "TikTok Shop",
                "Вещь можно увидеть в ролике или эфире и открыть её карточку во время просмотра.",
            )
            + note(
                "ВКонтакте",
                "Сообщество объединяет витрину, сообщения и записи. Товар уже можно прикрепить к публикации.",
            ),
        ),
        col(
            "star",
            "Повторная покупка",
            '<p class="sub">Покупатели с двумя и более заказами за сентябрь, по данным кейса</p>'
            + bar("ВКонтакте", 19, "19,0%", 30)
            + bar("Партнёр 1", 26.6, "26,6%", 30, grey)
            + stem(
                "Путь покупателя",
                [
                    ("Новый товар", "Открывает вещь из записи сообщества."),
                    ("Отложенная покупка", "Находит сохранённое и проверяет условия."),
                ],
            )
            + note(
                "Тест сохранённых товаров",
                "Случайно делим прежних покупателей пополам. Одни видят подборку, другие обычный Маркет. Сравним долю купивших снова за 30 дней.",
                "mint",
            ),
        ),
    ),
)


def levels():
    return (
        '<div class="levels">'
        + "".join(
            f"<div><b>{num}</b><span>{label}</span></div>"
            for num, label in [
                ("9 754", "все бизнесы"),
                ("3 961", "есть активный товар"),
                ("1 117", "есть просмотры товарного контента"),
                ("493", "подходит число подписчиков"),
            ]
        )
        + "</div>"
    )


def segment_weight():
    rows = []
    for label, icon, key in [
        ("Бизнесы", "shop", "businesses"),
        ("Заказы", "cart", "orders"),
    ]:
        count, total = pilot[key], audit["totals"][key]
        percent = 100 * count / total
        rows.append(
            f'<div class="segment-weight-row">{img(f"icon-{icon}.svg")}'
            f'<span>{label} <small>{n(count)} из {n(total)}</small></span>'
            f'<b>{comma(percent)}%</b><div class="segment-rail">'
            f'<i style="width:{percent:.3f}%"></i></div></div>'
        )
    return '<figure class="segment-weight"><figcaption>Доля сегмента в выборке</figcaption>' + "".join(rows) + "</figure>"


def order_mix():
    selling, total = pilot["selling"], pilot["businesses"]
    share = 100 * selling / total
    return (
        f'<figure class="order-mix"><figcaption>{n(total)} сообщества в сентябре</figcaption>'
        f'<div class="mix-rail" aria-hidden="true"><i style="width:{100 - share:.3f}%"></i></div>'
        f'<div class="mix-labels"><span><b>{comma(100 - share)}%</b>без заказов</span>'
        f'<span><b>{comma(share)}%</b>с заказами</span></div></figure>'
    )


slide(
    "Аудитория",
    "Целевые сообщества",
    grid(
        col(
            "user",
            "Как отобрали магазины",
            levels()
            + item(
                "Размер аудитории",
                "От 1 001 до 100 000 подписчиков включительно.",
            )
            + segment_weight(),
        ),
        col(
            "chart",
            "Доля магазинов с заказом",
            '<p class="sub">Сравниваем сообщества с активным товаром внутри диапазона подписчиков. Сентябрь 2026 года.</p>'
            + item(
                "Больше 1 тыс., до 10 тыс.",
                "С товарными просмотрами 84 из 396. Без просмотров 66 из 1 059.",
            )
            + bar("С просмотрами", 84 / 396 * 100, "21,2%", 40)
            + bar("Без просмотров", 66 / 1059 * 100, "6,2%", 40, grey)
            + item(
                "Больше 10 тыс., до 100 тыс.",
                "С товарными просмотрами 37 из 97. Без просмотров 25 из 132.",
            )
            + bar("С просмотрами", 37 / 97 * 100, "38,1%", 40)
            + bar("Без просмотров", 25 / 132 * 100, "18,9%", 40, grey),
        ),
        col(
            "shop",
            "Два сценария для продавца",
            order_mix()
            + item(
                "372 сообщества пока без заказов",
                "На старте показываем товар с неполными условиями. Продавец исправляет карточку и проверяет её со стороны покупателя.",
            )
            + item(
                "121 сообщество уже продаёт",
                "В кабинете нужны очередь заказов, выдачи, причины отмен и результат по каждой записи.",
            )
            + item(
                "Первый вход в кабинет",
                "В разделе «Обзор» продавец открывает задачу «Подготовить товар». Кабинет ведёт к черновику, где можно добавить адрес самовывоза и прикрепить товар к записи.",
            ),
        ),
    ),
)


def short_journey():
    from journey import steps

    rows = []
    for label, key, color in [
        ("Этап", 0, "#e2f3eb"),
        ("Продавец", 2, "#eef6ed"),
        ("Покупатель", 3, "#e8f2fe"),
        ("Работа сервиса", 5, "#f0edfa"),
        ("Что измерим", 6, "#f1f5f9"),
    ]:
        cells = []
        for stage in stages:
            content = escape(stage[key])
            if key == 0:
                content = f"<small>{stage[1]}</small><b>{content}</b>"
            cells.append(f'<div><span style="background:{color}">{content}</span></div>')
        rows.append(f'<div class="cjm-band"><strong>{label}</strong>{"".join(cells)}</div>')
    chart = []
    for role, color in [("buyer", "#0566ce"), ("seller", "#10735b")]:
        previous = None
        for phase in range(6):
            ratings = [s.feeling for s in steps[4*phase:4*phase+4] if s.actor == role]
            if not ratings:
                previous = None
                continue
            x, y = 90 + phase * 176, 38 - ratings[-1] * 10
            if previous:
                chart.append(f'<line x1="{previous[0]}" y1="{previous[1]}" x2="{x}" y2="{y}" stroke="{color}" stroke-width="2"/>')
            if role == "buyer":
                chart.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{color}" stroke="white" stroke-width="1.5"/>')
            else:
                chart.append(f'<rect x="{x-4}" y="{y-4}" width="8" height="8" rx="1" fill="{color}" stroke="white" stroke-width="1"/>')
            previous = (x,y)
    guides = "".join(f'<line x1="0" x2="1056" y1="{y}" y2="{y}" stroke="#dce6ef"/>' for y in [18,38,58])
    plot = f'<svg viewBox="0 0 1056 70" preserveAspectRatio="none" role="img" aria-label="Оценки эмоций по последнему шагу каждой роли на этапе. Гипотеза команды.">{guides}{"".join(chart)}</svg>'
    style = """<style>
    #p6 .cjm-band{display:grid;grid-template-columns:145px repeat(6,minmax(0,1fr));border-bottom:1px solid #d9e5ec}
    #p6 .cjm-band>strong{align-self:center;font-size:16px;color:#274b65}
    #p6 .cjm-band>div{padding:3px 4px;border-left:1px solid #e0e8ed;display:flex}
    #p6 .cjm-band span{display:block;padding:5px 8px;font-size:15.5px;line-height:1.21;border-radius:3px;width:100%}
    #p6 .cjm-band small{display:block;font-size:12px;color:#416569}
    #p6 .cjm-band b{font-size:16.5px}
    #p6 .cjm-chart{display:grid;grid-template-columns:145px 1fr;align-items:center;border-bottom:1px solid #d9e5ec}
    #p6 .cjm-chart strong{font-size:16px;color:#274b65}
    #p6 .cjm-chart small{display:block;font-size:11px;color:#4a657c;margin-top:3px}
    #p6 .cjm-chart svg{width:100%;height:59px}
    #p6 .maptail{display:flex;justify-content:flex-end;margin-top:7px}
    #p6 .maptail .scan img{width:102px;height:102px}
    #p6 .cjm-key{font-size:12px;line-height:1.3;color:#29455b}
    #p6 .cjm-key span{display:block}
    </style>"""
    return style + "".join(rows) + '<div class="cjm-chart"><div><strong>Эмоции</strong><small>От −2 до +2, гипотеза</small><div class="cjm-key"><span style="color:#0566ce">● Покупатель</span><span style="color:#10735b">■ Продавец</span></div></div>' + plot + '</div>'


slide(
    "Продукт",
    "Карта пути продавца и покупателя",
    short_journey()
    + '<div class="maptail">'
    + qr(
        "journey",
        "journey.html",
        "Открыть карту пути",
        "24 шага, задачи участников, барьеры и Service Blueprint",
    )
    + "</div>",
)


def device(icon, title, asset, label, body):
    return (
        '<article class="devicecell"><h2 class="sectiontitle">'
        + img(f"icon-{icon}.svg")
        + title
        + "</h2>"
        + img(asset, "device", label)
        + f"<h3>{label}</h3><p>{body}</p></article>"
    )


slide(
    "Продукт",
    "Кабинет сообщества и покупка в VK",
    '<div class="devicegrid">'
    + device(
        "shop",
        "Кабинет продавца",
        "mac-shop.webp",
        "Обзор магазина",
        "Продавец видит новые заказы, вопросы покупателей и карточки, которым не хватает условий. Из обзора он открывает конкретную задачу.",
    )
    + device(
        "post",
        "Клипы",
        "phone-clip.webp",
        "Товар под видео",
        "Покупатель нажимает на кружку под клипом, проверяет цену и выбирает способ получения. Источник сохраняется в заказе.",
    )
    + device(
        "check",
        "Заказ покупателя",
        "phone-order.webp",
        "Вопрос и ответ",
        "Переписка хранится рядом с номером заказа. После выдачи покупатель видит новый статус, при отмене получает причину.",
    )
    + "</div>"
    + '<div class="producttail">'
    + qr("prototype", "prototype/", "Попробовать магазин", "Оформите самовывоз за покупателя и отметьте выдачу за продавца.")
    + '<div class="order-example"><b>Заказ из клипа «После обжига»</b>'
    '<ol><li>Кружка «Утро»<small>1&nbsp;450&nbsp;₽</small></li><li>Самовывоз<small>В мастерской</small></li>'
    '<li>Выдан<small>В обоих кабинетах</small></li></ol></div></div>',
)

slide(
    "Запуск",
    "План запуска и экономика",
    '<div class="financegrid">'
    + col(
        "post",
        "Первые 12 недель",
        stem(
            "Пилот",
            [
                (
                    "Недели 1–3",
                    "12–16 интервью с продавцами и 6–8 покупательских тестов. Выясняем, где меняются условия покупки.",
                ),
                (
                    "Недели 4–8",
                    "50–100 сообществ проходят путь от публикации до выдачи. Сверяем события, остатки и причины отмен.",
                ),
                (
                    "Недели 9–12",
                    "Сверяем заказы и выдачи, оцениваем разброс и набираем магазины для рандомизированного теста.",
                ),
            ],
        )
        + note(
            "Условие расширения",
            "В обеих ролях совпадают номер и статус заказа. Каждая отмена возвращает товар в остаток один раз.",
        ),
    )
    + col(
        "chart",
        "Накопленный поток",
        '<p class="sub">Базовый сценарий после запуска, млн ₽</p>'
        + chart()
        + '<div class="axislabel">Месяц после запуска</div>'
        + '<div class="chartfacts"><div><b>3-й месяц</b><span>Первый положительный месяц, +5 тыс. ₽.</span></div><div><b>17-й месяц</b><span>Накопленный поток впервые выше нуля, +145 тыс. ₽.</span></div></div>'
        + item("5,195 млн ₽", "Пиковая потребность в финансировании на 2-м месяце, включая 4,8 млн ₽ на запуск."),
    )
    + col(
        "check",
        "Условия расчёта",
        stat("6 000", "активных продавцов к 6-му месяцу в базовом сценарии")
        + item(
            "135 ₽ вклада на магазин",
            "20% продавцов покупают дополнительное продвижение на 1 500 ₽ в месяц. Маржа 65%, поддержка 60 ₽ на активного продавца.",
        )
        + note(
            "+410 тыс. ₽ в месяц",
            "Из 1,17 млн ₽ маржи вычитаем 360 тыс. ₽ на поддержку и 400 тыс. ₽ постоянных расходов.",
            "mint",
        ),
    )
    + "</div>",
)


slide(
    "Приложение",
    "Данные кейса и причины потери заказа",
    grid(
        col(
            "shop",
            "Выборка бизнесов",
            stat(
                n(audit["unique_business_ids"]),
                "бизнеса в синтетической выборке за сентябрь 2026 года",
            )
            + item(
                "3 478 оформлений",
                "Заказ получили 298 бизнесов. Оборот по строкам бизнесов составил 9,97 млн ₽.",
            )
            + item(
                "Настройки в сентябре",
                "У 268 бизнесов с заказом выключена оплата, у 14 выключено оформление. Дата смены настроек неизвестна.",
            )
            + note(
                "Влияние крупных магазинов",
                "На десять крупнейших приходится 54,0% заказов выборки. Это увеличивает требуемый размер эксперимента.",
            ),
        ),
        col(
            "chart",
            "Проверка итогов по VK",
            '<p class="sub">Оформленные заказы за один и тот же период в двух листах исходной книги</p>'
            + bar("Сумма по категориям", 435285, "435 285", 450000)
            + bar("Общий итог", 413740, "413 740", 450000, navy)
            + stat("+21 545", "оформлений составляет расхождение")
            + item(
                "Знаменатели",
                "Для доли сегмента берём 3 478 заказов в листе бизнесов. Доли источников считаем по открытиям карточек. Индивидуальные маршруты в книге не записаны.",
            ),
        ),
        col(
            "check",
            "Гипотезы о причинах",
            '<div class="causes"><strong class="rootnode">Магазин не доходит до выдачи</strong><ul>'
            '<li><b>Товар не виден покупателю</b><ul><li>Продавец оставил его в черновиках<ul><li>Не указал, где забрать покупку</li></ul></li></ul></li>'
            '<li><b>Покупатель не открыл карточку</b><ul><li>В записи нет ссылки на вещь<ul><li>Продавец опубликовал фото без товарной метки</li></ul></li></ul></li>'
            '<li><b>Оформленный заказ не забрали</b><ul><li>Стороны не согласовали время<ul><li>Продавец пропустил вопрос о самовывозе</li></ul></li></ul></li>'
            '</ul></div>',
        ),
    ),
)

alternatives = [
    (
        "Продажа из записи",
        "У товара есть просмотры, заказов мало.",
        "Оформления на бизнес за 30 дней, доля выдач.",
        "4,8 млн ₽ на запуск за 12 недель.",
        "Заказы перейдут из витрины в ленту.",
        "Проверить выдачу на 50–100 магазинах, затем сравнить все заказы VK с контролем.",
    ),
    (
        "Привлечение магазинов",
        "Мало сообществ с доступным ассортиментом.",
        "Затраты на магазин, впервые выдавший заказ.",
        "Бюджет набора плюс часы сопровождения × ставка.",
        "Новые магазины останутся без заказов.",
        "Начать с одной группы. Расширять, если вклад новых магазинов покроет привлечение.",
    ),
    (
        "Главная Маркета",
        "Покупатель потерял отложенный товар.",
        "Доля купивших повторно за 30 дней.",
        "Часы разработки и аналитики × их ставки.",
        "Маркет заберёт заказы из других разделов.",
        "Показать подборку части покупателей. Расширять при росте повторных покупок во всём VK.",
    ),
    (
        "Товары у авторов",
        "Публикации магазина мало кто видит.",
        "Затраты на дополнительную выдачу.",
        "Гонорары за ролики плюс стоимость производства.",
        "Просмотры вырастут без новых выдач.",
        "Сравнить магазины с роликом автора и без. Продолжать, если вклад добавочных выдач покроет расходы.",
    ),
    (
        "Скидка на покупку",
        "Цена мешает первой покупке.",
        "Вклад после скидки, повторные выдачи.",
        "Размер скидки × число заказов со скидкой.",
        "Субсидию получат те, кто и так купил бы.",
        "Сравнить с группой без скидки. Сохранить, если вклад от дополнительных покупок покроет субсидии.",
    ),
]


def decision(row, i):
    title, obstacle, metric, cost, risk, next_step = row
    return (
        f'<div class="decision {"chosen" if i == 0 else ""}">'
        f'<div><h3>{title}</h3><p>{obstacle}</p></div><p>{metric}</p>'
        f'<p>{cost}</p><p>{risk}</p><p>{next_step}</p></div>'
    )


slide(
    "Приложение",
    "Выбор инициативы",
    '<div class="decision labels"><b>Инициатива и препятствие</b><b>Что измеряем</b><b>Из чего состоят затраты</b><b>Основной риск</b><b>Решение после проверки</b></div>'
    + "".join(decision(row, i) for i, row in enumerate(alternatives)),
)

slide(
    "Приложение",
    "Обработка заказа в магазине сообщества",
    '<div class="grid processgrid">'
    + col(
        "post",
        "Как проходит заказ",
        (BASE / "assets/order-flow.svg")
        .read_text()
        .replace(
            "<svg ",
            '<svg class="process" role="img" aria-label="Действия продавца, покупателя и магазина" ',
            1,
        )
        .replace('height="334"', "")
        + note(
            "Если товар закончился",
            "Перед оформлением проверяем цену, количество и способ получения. При изменении условий покупатель видит причину и может обновить карточку.",
        ),
    )
    + col(
        "shop",
        "Что сохраняется в кабинете",
        stem(
            "Карточка товара",
            [
                (
                    "Публикация",
                    "У каждого поста свой номер. Покупку из ленты связываем с той записью, из которой открыли товар.",
                ),
                (
                    "Оформление",
                    "Фиксируем цену, количество, адрес или срок и стоимость доставки. Повторная отправка сохраняет номер заказа.",
                ),
                (
                    "Исполнение",
                    "Вопрос и ответ, время выдачи или причина отмены доступны в карточке заказа.",
                ),
            ],
        )
        + note(
            "Для запуска внутри VK",
            "Авторизация через VK ID, платёжные статусы и статусы службы доставки.",
            "mint",
        ),
    )
    + "</div>",
)

base = model["scenarios"][1]


def scenario_flows():
    # Widths share one linear scale, from minus 0.5 to plus 3 million roubles.
    x_zero = 54
    pixels_per_million = 100
    svg = []
    for i, scenario in enumerate(model["scenarios"]):
        y = 22 + 51 * i
        monthly = scenario["net_monthly_steady"] / 1_000_000
        x_end = x_zero + monthly * pixels_per_million
        sign = "+" if monthly >= 0 else "−"
        sign_label = sign + comma(abs(monthly), 3)
        color = "#ae4e40" if monthly < 0 else blue
        svg.append(
            f'<text x="5" y="{y}" class="flow-name">{scenario["scenario"]}</text>'
            f'<text x="137" y="{y}" class="flow-count">{n(scenario["active"])} продавцов</text>'
            f'<text x="357" y="{y}" text-anchor="end" class="flow-amount" fill="{color}">{sign_label}</text>'
            f'<rect x="{min(x_end, x_zero):.2f}" y="{y + 8}" width="{abs(x_end - x_zero):.2f}" '
            f'height="11" rx="2" fill="{color}"/>'
            f'<path d="M{x_zero} {y + 4}v19" class="flow-zero"/>'
        )
    ticks = []
    for value in (-0.5, 0, 1, 2, 3):
        x = x_zero + value * pixels_per_million
        anchor = "start" if value == -0.5 else "end" if value == 3 else "middle"
        label = "−0,5" if value < 0 else str(value)
        ticks.append(
            f'<path d="M{x} 152v4" class="flow-tick"/><text x="{x}" y="173" '
            f'text-anchor="{anchor}" class="flow-axis">{label}</text>'
        )
    return (
        '<figure class="scenario-flows"><figcaption>Денежный поток при плановом числе продавцов, млн ₽ в месяц</figcaption>'
        '<svg viewBox="0 0 361 178" role="img" aria-label="Месячный денежный поток в трёх сценариях">'
        + "".join(svg)
        + '<path d="M4 152H354" class="flow-tick"/>'
        + "".join(ticks)
        + '</svg></figure>'
    )


slide(
    "Приложение",
    "Финансовая модель",
    grid(
        col(
            "chart",
            "Расходы на запуск",
            stat("4,8 млн ₽", "разовые вложения по плану запуска")
            + "".join(
                bar(title, cash, label, 3.15, color)
                for title, cash, label, color in [
                    ("Разработка (9 чел.-мес.)", 3.15, "3,15 млн ₽", blue),
                    ("Настройка аналитики", 0.6, "600 тыс. ₽", navy),
                    ("Исследование и подключение", 0.45, "450 тыс. ₽", navy),
                    ("Инфраструктура", 0.3, "300 тыс. ₽", grey),
                    ("Резерв", 0.3, "300 тыс. ₽", grey),
                ]
            ),
        ),
        col(
            "shop",
            "Доходы и расходы в месяц",
            item(
                "1,8 млн ₽ выручки в месяц",
                "Допускаем, что из 20 000 магазинов подключатся 6 000. У 1 200 из них расходы на продвижение вырастут на 1 500 ₽ в месяц.",
            )
            + item(
                "410 тыс. ₽ после расходов",
                "Маржа 65% даёт 1,17 млн ₽. Из них 360 тыс. ₽ уходит на поддержку и 400 тыс. ₽ на постоянные расходы.",
            )
            + item(
                "2 963 активных магазина",
                "Месячный вклад одного магазина 135 ₽. Этого числа достаточно для покрытия постоянных расходов.",
            )
            + note(
                "Порог затрат на продвижение",
                "При 6 000 магазинах для покрытия расходов нужны 780 покупателей продвижения по 1 500 ₽ в месяц (13%).",
            ),
        ),
        col(
            "check",
            "Три сценария",
            scenario_flows()
            + item("Итог за 24 месяца", "+3,015 млн ₽ в базовом сценарии.")
            + qr(
                "model",
                "model.xlsx",
                "Скачать расчёты",
                "Excel с помесячным потоком и формулами",
            ),
        ),
    ),
)

slide(
    "Приложение",
    "Как проверить прирост заказов",
    grid(
        col(
            "user",
            "Дизайн эксперимента",
            item(
                "Единица сравнения",
                "Случайно распределяем бизнесы внутри групп по размеру аудитории, тематике и наличию заказов до теста.",
            )
            + item(
                "Главный показатель",
                "Все оформленные внутри VK заказы за 30 дней в расчёте на один назначенный бизнес. Учитываем заказы со всех точек входа.",
            )
            + item(
                "Освоение инструмента",
                "Число бизнесов, впервые опубликовавших запись с готовым товаром, делим на число бизнесов, которым предложили инструмент.",
            )
            + note(
                "Что ещё сравниваем",
                "Долю выданных и отменённых заказов, жалобы покупателей и расходы магазинов на рекламу в каждой группе.",
            ),
        ),
        col(
            "chart",
            "Сколько участников потребуется",
            '<p class="sub">На одну группу при среднем 3,79 и выборочном отклонении 18,49 заказа за сентябрь</p>'
            + "".join(
                bar(
                    "Цель +" + str(round(x["lift"] * 100)) + "%",
                    x["per_arm"],
                    n(x["per_arm"]),
                    38000,
                    blue if x["lift"] == 0.2 else grey,
                )
                for x in pilot["sensitivity"]
            )
            + item(
                "Доля продавцов с заказом",
                "Для роста с 24,5% до 29,5% ориентир составляет 1 238 бизнесов на группу, всего 2 476.",
            )
            + note(
                "Ограничение пилота",
                "493 подходящих бизнесов в исходной выборке мало для измерения +20%. На 50–100 магазинах можно проверить путь и сбор событий.",
                "mint",
            ),
        ),
        col(
            "check",
            "Риски эксперимента",
            item(
                "Заказы перешли из другого раздела",
                "Смотрим общий результат по VK. Рост в ленте может сопровождаться падением в витрине.",
            )
            + item(
                "Рост дали несколько магазинов",
                "Сравним распределение заказов и долю продавцов с заказом. Правила работы с выбросами фиксируем заранее.",
            )
            + item(
                "Оформлений больше, выдач меньше",
                "Разбираем причины отмен по группам и проверяем, где менялись обещанные условия.",
            ),
        ),
    ),
)

slide(
    "Приложение",
    "Материалы команды и источники",
    grid(
        col(
            "shop",
            "Материалы для жюри",
            qr(
                "jury",
                "",
                "Открыть страницу команды",
                "Прототип магазина, карта пути и расчёты",
            )
            + source(
                "Полная карта пути",
                "24 шага, точки контакта, препятствия и процессы магазина.",
                PUBLIC + "journey.html",
            )
            + source(
                "Расчёты команды",
                "Сегменты, источники открытий, заказы, сценарии и размер эксперимента.",
                PUBLIC + "model.xlsx",
            )
            + source(
                "Презентация в PDF",
                "Восемь основных слайдов и шесть приложений.",
                PUBLIC + "slides.pdf",
            ),
        ),
        col(
            "chart",
            "Данные и постановка",
            source(
                "Страница кейса VK",
                "На сайте организаторов описана задача. В задании для команд критерии приведены на с. 8–9, вопросы к стратегии на с. 20.",
                "https://vk-case-champ.ru/#track",
            )
            + source(
                "Исходная книга чемпионата",
                "Сентябрь 2026 года. Бизнесы, общие итоги, категории, источники, дни, покупатели и регионы.",
            )
            + source(
                "Консультация экспертов VK",
                "13:05 о приоритете заказов, 22:15 об оплате вне VK, 46:00 о различии витрины и Маркета.",
            ),
        ),
        col(
            "post",
            "Продукты и каналы",
            source(
                "VK Education",
                "Раздел о магазине на с. 23, товарные метки на с. 37, статистика сообщества на с. 44.",
                "https://object2-ac.vk-apps.com/vk-education-0554ff56-27eb-4093-a702-685722cef6d9/media/94/d9943f73e80741b3b0b18a183d925bbd.pdf",
            )
            + source(
                "Ozon для продавцов",
                "По ссылке на магазин покупатель может посмотреть весь ассортимент продавца.",
                "https://t.me/ozonmarketplace/2913?embed=1",
            )
            + source(
                "Авито для бизнеса",
                "Сообщения в объявлении и обсуждение условий сделки в чате.",
                "https://t.me/avito_b2b/862?embed=1",
            )
            + source(
                "TikTok Shop",
                "Покупка из видео, прямого эфира и витрины профиля.",
                "https://newsroom.tiktok.com/introducing-tiktok-shop?lang=en",
            )
            + source(
                "VKUI",
                "Компоненты и фирменный знак для интерфейса магазина.",
                "https://vkui.io/",
            ),
        ),
    )
    + '<footer class="method-note"><div><h2>Предложение команды</h2>'
    '<p>Начать с магазинов, чьи товары уже смотрят. По исходной книге проверили отбор 493 сообществ и пересчитали 1&nbsp;869 заказов. '
    'Сверили три финансовых сценария и прошли путь от клипа до выдачи заказа.</p></div>'
    '<div><h2>Как использовали ИИ</h2><p>С OpenAI Codex сравнивали гипотезы, писали код расчётов и прототипа, '
    'готовили слайды. В Whisper расшифровали консультацию VK. Для портретов сравнили маски ImageGen и Apple Vision.</p></div></footer>',
)

if len(pages) != 14:
    raise ValueError("The case deck must contain eight main slides and six appendices")
(BASE / "index.html").write_text(
    '<!doctype html><html lang="ru"><meta charset="utf-8"><title>'
    + case
    + '</title><link rel="stylesheet" href="brand.css"><body>'
    + "".join(pages)
    + "</body></html>"
)
(ROOT / "docs/jury/journey.html").write_text(render_page())
