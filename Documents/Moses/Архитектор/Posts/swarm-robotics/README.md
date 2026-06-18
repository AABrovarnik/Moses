# Управление роем — обзор

Серия заметок по моделям управления роем автономных агентов. Цель — собрать практический обзор архитектур, алгоритмов и поведения при отказах для разных типов агентов.

## Оглавление

1. **Глава 1. Базовые архитектуры** — централизованная, децентрализованная, иерархическая. Лидерство, эмерджентность, деградация.
   См. `01-architecture-overview.md`
2. **Глава 2. Воздушные дроны (БПЛА)** — БПЛА, военные рои (Perdix, LOCUST), световые шоу, доставка.
   См. `02-uav-swarm.md`
3. **Глава 3. IoT-устройства и сенсорные сети** — mesh-сети, протоколы (MQTT/CoAP/Thread), энергоэффективность.
   См. `03-iot-swarm.md`
4. **Глава 4. Программные агенты и LLM-рой** — эволюция MAS, фреймворки (CrewAI, LangGraph, AutoGen, Swarm), проблемы LLM-роёв.
   См. `04-software-agents.md`
5. **Глава 5. Наземные роботы** — Kiva, Locus, Spot, военные, доставка, NASA CADRE.
   См. `05-ground-robots.md`
6. **Глава 6. Алгоритмы глубже** — PSO, ACO, BFT — с математикой, интуицией, применениями.
   См. `06-algorithms-deep.md`
7. **Глава 7. Конкретный сценарий: SAR** — поисково-спасательные операции, реальные кейсы, этика.
   См. `07-sar-scenario.md`
8. **Глава 8. Эмерджентное поведение и предсказуемость** — как проектировать предсказуемые рои, формальные методы.
   См. `08-emergence-predictability.md`
9. **Глава 9. Безопасность роя** — модель угроз, реальные инциденты, защита по слоям.
   См. `09-swarm-security.md`
10. **Глава 10. Экономика роя** — TCO, бизнес-модели, unit economics, инвестиции.
    См. `10-economics.md`
11. **Глава 11. Юридические аспекты роя** — liability, страхование, регуляторика (FAA/EASA/AI Act), эмерджентная ответственность.
    См. `11-legal-aspects.md`
12. **Глава 12. Этика автономных систем** — три этические рамки, trolley problem для роя, ethics by design, LAWS, XAI, value alignment, реальные инциденты, этический паспорт.
    См. `12-ethics.md`
13. **Глава 13. Дизайн роя: практическое руководство** — 7 вопросов до старта, выбор архитектуры, симуляторы, метрики, A/B-тесты, red team, чек-листы, типичные ошибки, шаблоны проектирования.
    См. `13-swarm-design.md`
14. **Глава 14. Будущее роя** — квантовые рои, биогибридные (Xenobots, спермботы), нано-рой, self-replicating (von Neumann), нейроморфные, edge AI, AGI-рой, прогнозы 2030/2040/2060.
    См. `14-future.md`
15. **Глава 15. Примеры кода** — CrewAI, LangGraph, AutoGen, OpenAI Swarm, паттерны, метрики.
    См. `15-code-examples.md`
16. **Глава 16. Конкретный сценарий #2: Умный город** — трафик, smart grid, экология, безопасность, дроны.
    См. `16-smart-city.md`
17. **Глава 17. Подводный рой (AUV)** — физика среды, акустическая связь, cooperative localization, сонары, реальные платформы (REMUS, Bluefin, Slocum, Hugin), сценарии (MCM, экология, наука), DARPA Hydra, CoCoRo, российские проекты.
    См. `17-underwater-swarm.md`
18. **Глава 18. Космический рой (формации спутников и межпланетные системы)** — орбиты и группировки, Walker constellation, ISL, DTN, GNSS-relative, formation flying, мегагруппировки (Starlink, Kuiper, OneWeb, Guowang), навигационные системы (GPS/ГЛОНАСС/Galileo/BeiDou), Sentinel, GRACE-FO, Proba-3, LISA, ADR, обслуживание (MEV, Astroscale), межпланетные кубсаты (MarCO, CAPSTONE, Hera), Breakthrough Starshot, юридические вопросы (Outer Space Treaty, Kessler).
    См. `18-space-swarm.md`

## Источники

- Kennedy J., Eberhart R., Shi Y. «Swarm Intelligence» (2001)
- Wooldridge M. «An Introduction to Multi-Agent Systems» (2009)
- Rubenstein M. et al. «Kilobot: A 14-gram robot for studying collective behavior» (2012)
- Reynolds C.W. «Flocks, Herds, and Schools: A Distributed Behavioral Model» (1987)
- Dorigo M., Birattari M. «Swarm Intelligence» — обзорная статья в Scholarpedia

## Связанные отчёты

- `../redteam-llm-swarm-review.md` — Red-team review архитектуры отказоустойчивого программного роя 3–5 LLM-агентов: вердикт, 5 сценариев отказа, MVP-план на 10–14 дней, выбор LLM (Claude Haiku 4.5 + Sonnet 4.6 + Gemini 2.5 Pro), chaos-тесты.
