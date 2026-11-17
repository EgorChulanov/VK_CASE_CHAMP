"""Segment and reconcile all seven case sheets; no extrapolation to the VK population."""
import json
import sys
from pathlib import Path
import pandas as pd

source = Path(sys.argv[1])
sheets = pd.read_excel(source, sheet_name=None)
b = sheets['Бизнесы']
summary = sheets['Маркет Вконтакте — итоги'].set_index('Метрика')
active = b[b['Число активных товаров в каталоге'] > 0].copy()
active['audienceBand'] = pd.cut(active['Число подписчиков'], [-1,1000,10000,100000,float('inf')], labels=['до 1 тыс.','1–10 тыс.','10–100 тыс.','100 тыс.+'])
active['hasProductContent'] = active['Просмотры товарного контента'] > 0
active['hasOrders'] = active['Заказы через чекаут'] > 0

segments=[]
for keys, group in active.groupby(['audienceBand','hasProductContent'],observed=True):
    segments.append({'audience':str(keys[0]),'content':bool(keys[1]),'businesses':len(group),'selling':int(group.hasOrders.sum()),'selling_share':float(group.hasOrders.mean()),'orders':int(group['Заказы через чекаут'].sum()),'median_subscribers':float(group['Число подписчиков'].median())})

topics=[]
for name,g in active.groupby('Тематика'):
    topics.append({'topic':name,'businesses':len(g),'selling':int(g.hasOrders.sum()),'orders':int(g['Заказы через чекаут'].sum()),'gmv':float(g['GMV через чекаут, ₽'].sum())})

reconciliations=[]
for name in ['Маркет Вконтакте — категории','Покупатели','Покупатели по регионам']:
    frame=sheets[name]
    for col in frame.select_dtypes('number').columns:
        total=float(frame[col].sum())
        market='Партнёр 1' if 'Партнёр' in col else 'Маркет Вконтакте'
        metric='Открытия карточки товара' if col.startswith('Открытия') else 'Оформленные заказы' if col.startswith('Заказы') else 'Уникальные покупатели за 30 дней'
        expected=float(summary.loc[metric,market])
        reconciliations.append({'sheet':name,'metric':col,'total':total,'overall':expected,'delta':total-expected,'missing_cells':int(frame[col].isna().sum())})

src=sheets['Маркет Вконтакте — источники']
base=src[~src['Источник'].str.startswith('в т.ч.')]
source_rows=[]
for _,r in base.iterrows():
    source_rows.append({'source':r['Источник'],'vk_opens':int(r['Маркет Вконтакте']),'vk_share':float(r['Маркет Вконтакте']/summary.loc['Открытия карточки товара','Маркет Вконтакте']),'partner_opens':int(r['Партнёр 1'])})

cat=sheets['Маркет Вконтакте — категории'].copy()
category_rows=[]
for _,r in cat.iterrows():
    category_rows.append({'category':r['Категория'],'opens':int(r.iloc[1]),'orders':int(r.iloc[2]),'orders_per_open':float(r.iloc[2]/r.iloc[1]) if r.iloc[1] else None,'partner_opens':int(r.iloc[3]),'partner_orders':int(r.iloc[4])})

buyers=sheets['Покупатели']
regions=sheets['Покупатели по регионам']
result={
    'within_audience_segments':segments,
    'topics_active_catalog':sorted(topics,key=lambda x:x['orders'],reverse=True),
    'aggregate_reconciliations':reconciliations,
    'sources':source_rows,
    'categories':category_rows,
    'business_order_concentration':{str(n):float(b.nlargest(n,'Заказы через чекаут')['Заказы через чекаут'].sum()/b['Заказы через чекаут'].sum()) for n in [1,10,50,100]},
    'zero_medians':{'orders':float(b['Заказы через чекаут'].median()),'gmv':float(b['GMV через чекаут, ₽'].median())},
    'buyer_female_share_visible':float(buyers.loc[buyers['Пол']=='Ж','Покупатели: Маркет Вконтакте'].sum()/buyers['Покупатели: Маркет Вконтакте'].sum()),
    'partner_unknown_region_share_visible':float(regions.loc[regions['Регион']=='Не указан','Покупатели: Партнёр 1'].sum()/regions['Покупатели: Партнёр 1'].sum()),
    'notes':['Subgroup associations are descriptive, not causal.','Category orders per open is an aggregate ratio, not a user-level conversion.','Suppressed groups and missing demographic/geographic attribution must remain visible.']
}
out=Path(__file__).parent/'market_analysis.json'
out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
