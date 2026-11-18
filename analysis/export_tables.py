"""Export presentation figures to a readable workbook from the checked analysis files."""
from pathlib import Path
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

base = Path(__file__).parent
market = json.loads((base/'market_analysis.json').read_text())
scenarios = json.loads((base/'scenarios.json').read_text())
pilot = json.loads((base/'pilot.json').read_text())
wb=Workbook()
wb.remove(wb.active)
def sheet(title, headers, values):
    ws=wb.create_sheet(title)
    ws.append(headers)
    for row in values: ws.append(row)
    ws.freeze_panes='B2'
    for i,col in enumerate(ws.columns,1):
        ws.column_dimensions[get_column_letter(i)].width=min(68,max(14,max(len(str(c.value)) for c in col)+3))
    tab=Table(displayName=f'Data{len(wb.worksheets)}',ref=ws.dimensions)
    tab.tableStyleInfo=TableStyleInfo(name='TableStyleMedium2',showRowStripes=True,showColumnStripes=False)
    ws.add_table(tab)
    for c in ws[1]: c.font=Font(name='Arial',bold=True,color='FFFFFF');c.fill=PatternFill('solid',fgColor='0876CE')
    return ws
sheet('Сегменты',['Аудитория','Просмотры контента','Бизнесы','Продающие','Доля продающих','Заказы'],[(r['audience'],'Есть' if r['content'] else 'Нет',r['businesses'],r['selling'],r['selling_share'],r['orders']) for r in market['within_audience_segments']])
sheet('Открытия',['Источник','VK','Доля открытий VK','Партнёр'],[(r['source'],r['vk_opens'],r['vk_share'],r['partner_opens']) for r in market['sources']])
sheet('Категории',['Категория','Открытия VK','Заказы VK','Открытия партнёра','Заказы партнёра'],[(r['category'],r['opens'],r['orders'],r['partner_opens'],r['partner_orders']) for r in market['categories']])
sheet('Экономика',['Сценарий','Месяц','Активные бизнесы','Денежный поток, ₽','Накопленный поток, ₽'],[(s['scenario'],m['month_after_launch'],m['active'],m['net_cash'],m['cumulative_cash']) for s in scenarios['scenarios'] for m in s['months']])
sheet('Размер теста',['Рост заказов','Дополнительные заказы на бизнес','Бизнесы на группу'],[(r['lift'],r['absolute_orders'],r['per_arm']) for r in pilot['sensitivity']])
for name,col in [('Сегменты','E'),('Открытия','C'),('Размер теста','A')]:
    for c in wb[name][col][1:]: c.number_format='0.00%'
wb.save(base/'VK-Cases.xlsx')
