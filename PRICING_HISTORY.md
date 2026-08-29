# Pricing History — Yardi Connector

Обязательный журнал: каждое выставление или изменение цен на функции этого
приложения фиксируется здесь — что изменилось, почему, и на основании
чего. Не переписывать прошлые записи — только дописывать новые сверху.

---

## 2026-08-22 — первичный прайсинг, до submit_for_review (по канону)

**Порядок соблюдён строго по `PRICING_POLICY.md` §1:** код готов → чистая
валидация (`imperal validate`: 0 errors, 0 warnings, 1 info) →
`deploy_app` (20/21 — тот же безобидный "нет `@ext.on_install`" info,
подтверждённо не блокер, см. Ironclad Connector с тем же 20/21) →
`save_pricing` → (этот шаг) → `submit_for_review` следующим.

**Шкала — строго фиксированная (`PRICING_POLICY.md` §2): 0, 8, 16, 20, 40.**

- `0` — `connect_yardi`, `disconnect_yardi`, `list_connections`
  (подключение/список подключений, без обращения к чужому Yardi API).
- `8` — простые read-функции (list/get) по properties, units, residents,
  leases, rent roll, transactions, invoices, purchase orders, job cost,
  budget, service requests, revenue data, renewals, guest activity,
  applications, WSDL introspection.
- `16` — write/mutating функции: import_yardi_contacts/charge/receipt/
  payable/invoice/purchase_order/revenue_update/renewal_selection/
  guest_card/application, create_yardi_service_request.
- `20` — `call_yardi_operation` (универсальный passthrough на ЛЮБУЮ SOAP
  операцию — дороже обычного write по непредсказуемой стоимости на
  стороне пользовательского Voyager).
- `40` — Tier-3 агрегирующие value-add отчёты: `audit_yardi_properties`,
  `get_yardi_delinquency_report`, `get_yardi_open_work_orders_report`.

**Метод применения — `developer.save_pricing` с `tool_prices` как
НАСТОЯЩИМ объектом (не строкой) + `revenue_split_dev=95` явным
параметром, `pricing_model="per_action"` явным параметром.**

Первый вызов в этой сессии вернул ошибку "did NOT save correctly" для
КАЖДОГО платного поля (все read/write/report функции), при этом
`connect_yardi`/`disconnect_yardi`/`list_connections` (цена 0) прошли
без жалобы. Это тот же класс платформенного несоответствия, что уже
задокументирован в Imperal Cloud task #2230 (`gitlab-cicd-connector`) и
task #2260 (`mirth-connect-connector`) — "object/array параметры доходят
как строка при первом вызове". Немедленный повторный вызов с ТЕМ ЖЕ
payload прошёл без единой ошибки (полный манифест вернулся в ответе).
Прецедент подтверждён на Ironclad/MuleSoft/Klaviyo/HubSpot/Webflow
Connector в этом же портфеле — тот же класс сбоя, то же исправление
(retry).

Read-back прямого подтверждения платформа не даёт (известное ограничение,
Imperal Cloud task #2113) — успешный вызов без вернувшейся ошибки принят
как подтверждение по тому же прецеденту, что и для предыдущих коннекторов.

**Итоговый файл со значениями:** `tool-prices.json` в этой директории.
