"""Audit the supplied synthetic workbook. Run with the XLSX path as argument."""
import collections
import hashlib
import json
import sys
from pathlib import Path
import openpyxl

source = Path(sys.argv[1])
workbook = openpyxl.load_workbook(source, read_only=True, data_only=True)
sheets = {sheet.title: list(sheet.values) for sheet in workbook}
rows = sheets['Бизнесы']
headers = rows[0]
records = [dict(zip(headers, row)) for row in rows[1:]]

def summarize(group):
    return {
        'businesses': len(group),
        'checkout_enabled': sum(r['Подключён чекаут'] == 1 for r in group),
        'payment_enabled': sum(r['Подключена оплата'] == 1 for r in group),
        'with_orders': sum(r['Заказы через чекаут'] > 0 for r in group),
        'orders': sum(r['Заказы через чекаут'] for r in group),
        'gmv_rub': sum(r['GMV через чекаут, ₽'] for r in group),
        'product_views': sum(r['Просмотры товарного контента'] for r in group),
        'card_opens_from_content': sum(r['Открытия карточки товара из контента'] for r in group),
        'ad_spend_rub': sum(r['Траты на рекламу всего, ₽'] for r in group),
    }

def segments(field):
    return {str(value): summarize([r for r in records if r[field] == value])
            for value in sorted({r[field] for r in records}, key=str)}

daily = sheets['Маркет Вконтакте — по дням']
summary = {r[0]: r[1:] for r in sheets['Маркет Вконтакте — итоги'][1:]}
checks = []
for daily_name, summary_name, column in [
    ('Показы товаров: Маркет Вконтакте', 'Показы товаров', 0),
    ('Показы товаров: Партнёр 1', 'Показы товаров', 1),
    ('Открытия карточки: Маркет Вконтакте', 'Открытия карточки товара', 0),
    ('Открытия карточки: Партнёр 1', 'Открытия карточки товара', 1),
    ('Заказы: Маркет Вконтакте', 'Оформленные заказы', 0),
    ('Заказы: Партнёр 1', 'Оформленные заказы', 1),
    ('Оплаченные заказы: Маркет Вконтакте', 'Оплаченные заказы', 0),
    ('GMV, ₽: Маркет Вконтакте', 'GMV, ₽', 0),
    ('GMV, ₽: Партнёр 1', 'GMV, ₽', 1),
]:
    total = sum(r[daily[0].index(daily_name)] for r in daily[1:])
    expected = summary[summary_name][column]
    checks.append({'metric': daily_name, 'daily_sum': total, 'summary': expected, 'delta': total-expected})

product = [r for r in records if r['Число активных товаров в каталоге'] > 0]
content = [r for r in product if r['Просмотры товарного контента'] > 0]
result = {
    'platform_comparison': {key: {'vk':summary[key][0], 'partner':summary[key][1]}
                            for key in ('Открытия карточки товара','Оформленные заказы','Доля повторных покупателей (2+ заказа), %')},
    'source_filename': source.name,
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'period': [str(daily[1][0]), str(daily[-1][0])],
    'schema': {name: {'records': len(data)-1, 'columns': data[0]} for name, data in sheets.items()},
    'unique_business_ids': len({r['ID бизнеса'] for r in records}),
    'missing_by_column': {h: sum(r[h] is None for r in records) for h in headers},
    'totals': summarize(records),
    'by_business_type': segments('Тип бизнеса (товары / услуги)'),
    'by_topic': segments('Тематика'),
    'by_checkout': segments('Подключён чекаут'),
    'candidate_segments': {
        'active_product_catalog': summarize(product),
        'catalog_and_product_content': summarize(content),
        'catalog_content_checkout_off': summarize([r for r in content if r['Подключён чекаут'] == 0]),
        'catalog_content_checkout_on': summarize([r for r in content if r['Подключён чекаут'] == 1]),
        'catalog_content_checkout_on_payment_off': summarize([r for r in content if r['Подключён чекаут'] == 1 and r['Подключена оплата'] == 0]),
    },
    'consistency': checks,
    'anomalies': {
        'orders_with_checkout_off': sum(r['Заказы через чекаут'] > 0 and r['Подключён чекаут'] == 0 for r in records),
        'orders_with_payment_off': sum(r['Заказы через чекаут'] > 0 and r['Подключена оплата'] == 0 for r in records),
        'gmv_with_zero_orders': sum(r['GMV через чекаут, ₽'] > 0 and r['Заказы через чекаут'] == 0 for r in records),
    },
    'limits': ['Synthetic data, September 2026 only.', 'No business ID in aggregate market sheets: do not join them to businesses.', 'Daily distinct buyers cannot be summed into monthly unique buyers.', 'Enabled flags are a snapshot, not adoption dates.', 'No causal interpretation of checkout subgroup differences.'],
}
output = Path(__file__).resolve().parent / 'dataset_audit.json'
output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str)+'\n')
print(json.dumps({k: result[k] for k in ['totals', 'by_business_type', 'candidate_segments', 'anomalies', 'consistency']}, ensure_ascii=False, indent=2))
