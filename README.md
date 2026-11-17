# Следующий заказ

Решение команды Digital Cat$ (Москва) для отборочного этапа VK Case Champ 2026.

[Скачать презентацию](presentation/Digital%20Cat%24_strategy_msk.pdf). Первые восемь страниц содержат решение, остальные четырнадцать раскрывают данные, альтернативы, экономику и эксперимент.

[Стратегия](docs/STRATEGY.md) · [Требования и критерии](docs/REQUIREMENTS.md) · [Расчёты по выборке](analysis/market_analysis.json) · [Экономические сценарии](analysis/scenarios.json)

Редактируемый источник презентации находится в presentation/build_deck.py. Скрипт читает расчёты из analysis и создаёт index.html. Скрипт render.mjs собирает PDF с помощью Node.js, Playwright и Chromium.
