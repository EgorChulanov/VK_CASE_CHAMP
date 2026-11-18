"""Calculate order dispersion and indicative power within the target segment."""
from pathlib import Path
import json
import math
import sys
import pandas as pd

businesses = pd.read_excel(sys.argv[1], sheet_name='Бизнесы')
group = businesses.loc[(businesses['Число активных товаров в каталоге'] > 0)
                       & (businesses['Просмотры товарного контента'] > 0)
                       & businesses['Число подписчиков'].between(1001, 100000)]
orders = group['Заказы через чекаут']
mean = float(orders.mean())
variance = float(orders.var())
rows = []
for lift in [0.10, 0.20, 0.30]:
    delta = mean * lift
    per_arm = math.ceil(2 * variance * (1.959964 + 0.841621)**2 / delta**2)
    rows.append({'lift': lift, 'absolute_orders': delta, 'per_arm': per_arm})
result = {'businesses':len(group), 'orders':int(orders.sum()), 'mean':mean,
          'sd':math.sqrt(variance), 'median':float(orders.median()),
          'selling':int((orders > 0).sum()), 'sensitivity':rows}
Path(__file__).with_name('pilot.json').write_text(json.dumps(result,indent=2)+'\n')
