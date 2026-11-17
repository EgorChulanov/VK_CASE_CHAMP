"""Planning scenarios, not a forecast. All commercial inputs are explicit assumptions."""
import json
import math
from pathlib import Path

investment = 4_800_000
fixedMonthly = 400_000
supportPerActive = 60
contributionMargin = 0.65
scenarios = [
    ('Осторожный', 10_000, 0.20, 0.15, 1000),
    ('Базовый', 20_000, 0.30, 0.20, 1500),
    ('Высокий', 40_000, 0.35, 0.25, 1800),
]
results=[]
for name,eligible,adoption,advertisers,spend in scenarios:
    active=eligible*adoption
    revenue=active*advertisers*spend
    unitContribution=advertisers*spend*contributionMargin-supportPerActive
    monthly=revenue*contributionMargin-active*supportPerActive-fixedMonthly
    cash=-investment
    payback=None
    months=[]
    for month in range(1,25):
        ramp=min(month/6,1)
        net=active*ramp*unitContribution-fixedMonthly
        cash+=net
        if cash>=0 and payback is None:payback=month
        months.append({'month_after_launch':month,'active':active*ramp,'net_cash':net,'cumulative_cash':cash})
    results.append({'scenario':name,'eligible_assumption':eligible,'adoption_assumption':adoption,'incremental_advertiser_share_assumption':advertisers,'incremental_spend_assumption_rub':spend,'active':active,'incremental_revenue_monthly':revenue,'contribution_per_active_rub':unitContribution,'net_monthly_steady':monthly,'breakeven_active':math.ceil(fixedMonthly/unitContribution) if unitContribution>0 else None,'payback_month_after_launch':payback,'cash_24_months':cash,'months':months})

p0=121/493
p1=p0+0.05
p=(p0+p1)/2
n=math.ceil(((1.959964*math.sqrt(2*p*(1-p))+0.841621*math.sqrt(p0*(1-p0)+p1*(1-p1))))**2/(p1-p0)**2)
result={'input_status':'All commercial inputs are planning assumptions, not dataset measurements. Historical baseline is descriptive, future control rate unknown.','investment_rub':investment,'fixed_monthly_rub':fixedMonthly,'support_per_active_month_rub':supportPerActive,'contribution_margin_assumption':contributionMargin,'cost_breakdown_rub':{'product_engineering_9_person_months_at_350000':3150000,'analytics_instrumentation':600000,'research_and_seller_onboarding':450000,'infrastructure':300000,'reserve':300000},'scenarios':results,'experiment':{'historical_selling_share':p0,'historical_businesses':493,'historical_selling':121,'mde_absolute':0.05,'alpha_two_sided':0.05,'power':0.8,'required_per_arm_normal_approximation':n,'required_total':2*n,'note':'Independent business-level randomization, no clustering or attrition adjustment. Re-estimate from pre-period and add expected attrition before recruitment.'}}
Path(__file__).with_name('scenarios.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({**result,'scenarios':[{k:v for k,v in r.items() if k!='months'} for r in results]},ensure_ascii=False,indent=2))
