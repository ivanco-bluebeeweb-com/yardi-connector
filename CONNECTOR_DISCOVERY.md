# Yardi Connector — Connector Discovery

**Дата discovery:** 2026-08-22
**Статус:** Ярусы 1-3 пройдены. Задача #2293 явно заявляла "максимальная
форма со всеми доступными функциями... для повышения эффективности" —
трактуется как "максимум" (Ярус 1+2+3), по прецеденту GitLab CI/CD/
CircleCI/MuleSoft/Power Automate/UiPath/Blue Prism/Automation Anywhere/
Cin7 Core/ShipStation/PagerDuty/Mirth Connect/Ironclad — §7 не требует
повторного вопроса Владу.

---

## 1. Целевой сервис и источники

Yardi Voyager — доминирующая PMS (property management system) для
многоквартирной, коммерческой, студенческой и институциональной
недвижимости. В отличие от каждого другого коннектора в портфеле,
**у Yardi нет единого публичного REST/JSON API.** Функциональность
экспонируется через семейство из **7 независимых "Standard Interfaces"**
— каждый отдельный SOAP 1.1 веб-сервис (`.asmx`), с собственным WSDL,
собственным набором операций и **собственным лицензионным ключом**
(`InterfaceLicense`), который клиент Yardi покупает и активирует
ОТДЕЛЬНО на каждый интерфейс через своего Yardi-представителя.

Прочитано 2026-08-22:
- `github.com/yhavin/yardi-sdk` (MIT, неофициальный, но open-source и
  читаемый целиком) — единственный источник, где перечислены РЕАЛЬНЫЕ
  имена SOAP-операций и их параметры по каждому из 7 интерфейсов
  (~150+ операций суммарно), полученные автором из живой работы с
  Yardi. Прочитаны `core.py` (обёртка `zeep` + `requests`, Basic-auth
  на транспортном уровне НЕ используется — сама SOAP-авторизация идёт
  полями внутри XML-тела) и все 7 файлов `endpoints/*.py` (полный
  список классов = полный список операций с типизированными полями).
- `apis.io/apis/yardi/yardi-common-data-api/`,
  `.../yardi-voyager-commercial-data-api/`,
  `.../yardi-billing-and-payments-api/`,
  `.../yardi-store-web-services-api/` — независимый OpenAPI-профиль от
  API Evangelist. **Явно помечен самим автором:** "Yardi publishes no
  specification for this interface; the OpenAPI ... has not been
  validated against a live endpoint." Используется только как
  вторичное подтверждение направления (ingress/egress), не как
  источник точных имён параметров — те берутся из yardi-sdk, где они
  видны в реальном рабочем коде.
- `yardi.com/company/interfaces/` — официальная маркетинговая страница
  Yardi, подтверждает семь опубликованных категорий Standard Interfaces
  и модель "по интерфейсу — отдельная лицензия" (партнёрская
  экосистема Interface Partners).
- Официального публичного developer-портала с точной спецификацией
  Yardi **не публикует** — WSDL выдаётся только зарегистрированным
  клиентам под их собственным URL вида
  `https://<host>.yardiasp<N>.com/<clienturl>/webservices/<Interface>.asmx?WSDL`.

---

## 2. Архитектурное решение — WSDL-интроспекция, а не статичный namespace

**Проблема:** SOAP-запрос требует три вещи: `targetNamespace` операции,
`SOAPAction` HTTP-заголовок, и сам XML envelope. Ни один официальный
источник не публикует единый фиксированный namespace для всех клиентов
Yardi — `zeep` (библиотека, которую использует yardi-sdk) решает это,
скачивая и парся WSDL клиента заранее. Захардкодить один namespace
("тот, что видел я в одном примере") означало бы фабрикацию контракта,
который может не совпасть с реальной инсталляцией другого клиента —
запрещено анти-фабрикационными правилами платформы.

**Решение:** `yardi_client.py` реализует **динамическую WSDL-интроспекцию
через stdlib `xml.etree.ElementTree`** (без `zeep`/`lxml` — портфель
Imperal последовательно избегает лишних зависимостей за пределами
`imperal-sdk`, см. `requirements.txt` каждого другого коннектора):

1. На каждый вызов операции клиент скачивает `<wsdl_url>?WSDL` (GET через
   `ctx.http`, без сторонних библиотек), парсит
   `wsdl:definitions/@targetNamespace` и находит нужный
   `wsdl:binding/wsdl:operation[@name=...]/soap:operation/@soapAction`.
   **Осознанно без `ctx.cache`:** ни один другой коннектор портфеля пока
   не использует `ctx.cache` (проверено — 0 совпадений по всему
   `Apps/`), а федеральный потолок TTL всё равно всего 300 секунд
   (`I-CACHE-TTL-CAP-300S`) — выигрыш от кэширования одного лёгкого GET
   на WSDL не оправдывает риск первого в портфеле непроверенного
   использования этого API у сервиса, который и так не протестирован
   против живого сервера (см. §8). Один лишний GET на вызов — разумная,
   консервативная цена корректности.
2. Собирается SOAP 1.1 envelope вручную (f-string с `xml.sax.saxutils.
   escape` на каждое значение) — тело операции содержит все её
   параметры ПЛЮС стандартный "Login-блок" (`UserName`, `Password`,
   `ServerName`, `Database`, `Platform`, `InterfaceEntity`,
   `InterfaceLicense`), как это делает каждый класс `*_Login`-суффикса
   в yardi-sdk.
4. Ответ парсится обратно в `dict` через универсальный
   ElementTree-конвертер (namespace-agnostic по локальному имени тега),
   с явной проверкой на `soap:Fault` (маппится на понятную ошибку, а не
   на generic 200 OK с XML-мусором внутри).

Это даёт: (а) честную работу на ЛЮБОЙ реальной инсталляции клиента без
угадывания её namespace, (б) единый код-путь для всех 150+ операций —
не нужно писать 150 разных XML-шаблонов вручную.

---

## 3. Классификация функционала (Ярус 1 — обязательный)

Аутентификация: **BYOK**, как и остальной портфель. Пользователь вводит
свои Yardi Voyager учётные данные — они не выдаются самим Imperal.

| Функция | Направление | Интерфейс |
|---|---|---|
| Подключение (ServerName/Database/Platform/UserName/Password/InterfaceEntity + per-interface WSDL URL + InterfaceLicense) | — | все |
| GetPropertyList / GetPropertyConfigurations | Ingress | Common Data |
| GetResidents / GetResidentData | Ingress | Common Data |
| GetRentroll | Ingress | Common Data |
| GetUnitInformation / GetCurrentUnitInformation | Ingress | Common Data |
| GetLeaseInformation | Ingress | Common Data |
| GetResidentTransactions_Login / GetResidentCharges_Login | Ingress | Billing & Payments |
| GetResidentBalances | Ingress | Billing & Payments |
| ImportCharge_Login / ImportReceipt_Login | Egress | Billing & Payments |
| GetVendors_Login / GetVendor_Login | Ingress | Billing & Payments / Vendor Invoicing |
| GetPayables / GetPayableByBatchId | Ingress | Vendor Invoicing |
| ImportPayable_Login | Egress | Billing & Payments / Vendor Invoicing |
| GetPurchaseOrders / ImportPurchaseOrder | Both | Vendor Invoicing |
| GetServiceRequests / CreateOrEditServiceRequests | Both | Service Requests |
| AvailableUnits (ILS) | Ingress | ILS/Guest Card |
| GetScheduledLeaseRenewals / ImportRenewSelectedLease | Both | Lease Renewals |
| ExportChartOfAccounts | Ingress | Billing & Payments / Vendor Invoicing |
| Ping / GetVersionNumber (health-check per interface) | Ingress | все |

## 4. Ярус 2 — расширение полноты

Полное покрытие каждого из 7 интерфейсов curated-обёртками с типизацией:
GetBudgets, GetJournalEntries, GetJobCost, ReversePayable,
GetInvoiceRegister, PostPayableBatch/ReviewPayableBatch/
OpenPayableBatch (workflow оплат), GetRetentionAmounts,
GetLeaseChargeInformation, GetOccupants, ImportContacts,
GetUnitTransferData, GetTenantLeaseDocuments (+Import), GetRawProperty_
Login/ImportRM_Login/ImportMR_Login (Revenue Management), GetLeaseOffers,
ImportLeaseRenewalRentableItems (Lease Renewals), GetCustomValues
(Service Requests), и т.д. — суммарно покрывает большую часть из ~150
операций как явные типизированные тулы.

## 5. Ярус 3 — полный доступ и добавленная ценность Imperal

- **`call_yardi_operation`** — универсальный passthrough-тул: имя
  интерфейса + имя операции + JSON-параметры → полный доступ к ЛЮБОЙ из
  ~150+ операций, включая редкие/специфичные для клиента, без
  необходимости писать отдельный wrapped-тул на каждую. Это единственный
  практичный способ дать "максимум" на сервисе такого масштаба без SOAP-
  спецификации, официально валидированной Yardi.
- **`get_delinquency_report`** (добавленная ценность Imperal) — сканирует
  `GetResidentBalances` по всем резидентам портфеля и подсвечивает тех,
  у кого отрицательный/просроченный баланс превышает порог — тот же
  паттерн, что `find_expiring_contracts` у Ironclad / `get_low_stock_
  report` у Shopify/Cin7.
- **`get_lease_expiration_report`** (добавленная ценность) — сканирует
  `GetLeaseInformation` и подсвечивает договоры аренды, истекающие в
  заданном окне дней — управляющим важно проактивно продлевать раньше
  оттока резидентов.
- **`audit_portfolio_health`** (добавленная ценность) — агрегированный
  снимок по всему портфелю объектов: занятость (rentroll), просрочка
  платежей, открытые заявки на обслуживание, истекающие договоры —
  единый health-report, как `audit_cloudhub_environment`/`audit_org`/
  `audit_estate` у других коннекторов.
- **`get_vacancy_report`** (добавленная ценность) — GetUnitInformation по
  статусу "vacant" агрегировано по объекту, с днями простоя.

---

## 6. Сознательно вне охвата

- **Store Web Services (SWS2)** — отдельный, устаревший интерфейс для
  ILS-листингов недвижимости под аренду через сторонние сайты (не то же
  самое, что "ILS/Guest Card" из основного семейства); слишком нишевый
  и слабо задокументированный даже неофициально — не входит в v1.
- **RESO Web API / Data Dictionary** — это отдельный ОТРАСЛЕВОЙ стандарт
  (не Yardi-специфичный), который Yardi может поддерживать как одну из
  многих MLS-интеграций; вне границ коннектора "к Yardi", тот же
  принцип, что "не тащить весь смежный стандарт в один коннектор".
- **Прямой доступ к базе данных Yardi (SQL)** — не веб-API, для крупных
  инсталляций доступен как отдельный, гораздо более рискованный канал;
  не строится, пока сам сервис не предложит для этого управляемую
  веб-поверхность.

## 7. Решение по объёму — заявлено явно пользователем

Пользователь: "разработай это приложение в максимальной форме со всеми
доступными функциями с их стороны и всеми возможными функциями внутри
нашего приложения для повышения эффективности" → Ярус 1 + 2 + 3,
подтверждения не требуется (см. прецедент выше).

---

## 8. Известное ограничение этой сборки — честно зафиксировано

Ни у Imperal, ни у автора нет живого доступа к реальной Yardi Voyager
инсталляции (WSDL-эндпоинт + реальный `InterfaceLicense`) для end-to-end
теста против настоящего сервера. Код построен строго по документированному
публичному контракту (реальные имена операций/параметров из yardi-sdk,
подтверждённая модель Login-параметров), но **не был прогнан против
живого Yardi-сервера** — тот же класс ограничения, что зафиксирован для
Iguana/IguanaX и Redox в их `PREPARATION.md`. Это не блокер для publish
(код и тесты валидны против документированного контракта), но именно
поэтому `submit_for_review` откладывается до подтверждения, что других
технических блокеров (деплой/валидация/цены) нет — см. итоговый отчёт.
