# Yardi Connector — UI component plan

Источники: `Docs/session-notes/UI_COMPONENT_VOCABULARY.md`, `UI_INTERFACE_STANDARD.md`,
`concepts/panels.md`. Основано на функционале `yardi-connector`.

## 1. Компоненты

| Экран | Примитивы | Почему именно эти |
|---|---|---|
| Sidebar (left) | `ui.Column`(align="start") + `ui.Text`(company) + `ui.Divider` + navigation `ui.ListItem`(Properties/Units/Leases/Work Orders/GL) + `ui.Button`("App settings") | Без карточек по стандарту. |
| Property List (center, `center_overlay=True`) | `ui.Stats`(Properties/Units/Occupancy rate) + `ui.DataTable`(name, address, unit count, occupancy %; sortable) | Табличный обзор портфеля объектов. |
| Unit List (property detail) | Back-button + `ui.DataTable`(unit#, status Badge occupied/vacant/notice, rent, tenant; sortable) | Табличный обзор юнитов объекта. |
| Lease Detail | Back-button + `ui.KeyValue`(tenant/rent/term/deposit) + `ui.Timeline`(lease events: signed→move-in→renewal→notice→move-out) + `ui.List`(documents) | Жизненный цикл аренды через `Timeline`. |
| Work Order Queue | `ui.Stats`(Open/In progress/Completed) + `ui.DataTable`(unit, description, priority Badge, status Badge, created; sortable) | Табличный поток заявок на обслуживание (Yardi "Work Orders"). |
| Work Order Detail | Back-button + `ui.KeyValue`(unit/tenant/technician assigned) + `ui.Timeline`(created→assigned→in progress→completed) + `ui.TextArea`(param_name="note", placeholder="Добавить заметку по заявке...") + `ui.Row`(Button "Assign Technician", "Mark Completed") | Стадии обработки work order. |
| GL/Ledger Viewer | `ui.DataTable`(date, account, debit, credit, balance; sortable) | Табличная выписка по счетам General Ledger. |
| Charge/Payment Entry | `ui.Form`(action="post_charge") + `ui.Select`(lease) + `ui.Select`(charge_code) + `ui.Input`(type="number", amount) | Проведение начисления — форма с прямым вводом суммы. |
| Owner/Investor Statement | `ui.KeyValue`(income/expenses/net for period) + `ui.DataTable`(line items) | Финансовая сводка для владельца/инвестора. |
| Renewal Pipeline | `ui.DataTable`(lease, expiration date, renewal status Badge offered/accepted/declined; sortable) | Табличный обзор предстоящих продлений аренды. |
| App Settings | `ui.Accordion`([Connections+Disconnect, Default Property, Webhooks CRUD]) | Централизованные настройки по стандарту. |

## 2. User flow (валидно по panel lifecycle)

1. **SESSION INIT** → `__panel__yardi_sidebar` рендерит company + разделы,
   `auto_action` открывает Property List.
2. Property List → Unit List → Lease Detail (стандартная drill-down цепочка
   через `ui.Call` с накоплением id-параметров).
3. Work Order Queue → Detail → "Assign Technician" → `ui.Dialog`(Select
   technician) → подтверждение → `ui.Call` → `refresh_panels`.
4. Charge/Payment Entry: Form напрямую из sidebar или из Lease Detail
   (кнопка "Post Charge"); после отправки — `refresh_panels` обновляет
   GL/Ledger Viewer.
5. Renewal Pipeline: клик по строке → Lease Detail того лизa.
6. App Settings: доступен из sidebar в любой момент.

## 3. Экраны/карточки (конкретно для этого приложения)

- **Screen: Sidebar** — ListItem секции: Properties, Units, Leases, Work
  Orders (Badge open count), GL.
- **Screen: Property List** — Stats(3) + DataTable(4 колонки).
- **Screen: Unit List** — DataTable(4 колонки).
- **Screen: Lease Detail** — KeyValue + Timeline + List(documents).
- **Screen: Work Order Queue** — Stats(3) + DataTable(5 колонок).
- **Screen: Work Order Detail** — KeyValue + Timeline + TextArea + Row(2 Button).
- **Screen: GL/Ledger Viewer** — DataTable(5 колонок).
- **Screen: Charge/Payment Entry** — Form(3 поля).
- **Screen: Owner/Investor Statement** — KeyValue + DataTable.
- **Screen: Renewal Pipeline** — DataTable(3 колонки).
- **Screen: App Settings** — Accordion(3 секции).

Ограничение SDK, учтённое в плане: нет собственного примитива для visual
rent-roll grid с построчным редактированием множества полей сразу — General
Ledger и rent roll показываются как read-only DataTable, изменения проводятся
через отдельные формы (Charge/Payment Entry), не инлайн-редактированием
таблицы.
