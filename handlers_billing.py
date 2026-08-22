"""Billing & Payments interface handlers -- resident transactions, charges,
receipts, payables, vendor lookups, plus a value-add delinquency report
built from GetResidentTransactions_ByChargeDate_Login (Imperal-side
aggregation, not a native Yardi operation -- see schemas.py's
AuditReport-family docstring pattern).
"""
from __future__ import annotations

from datetime import date

from imperal_sdk import ActionResult

import yardi_client as yc
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    ResidentTransactionsParams, ImportChargeParams, ImportReceiptParams,
    ImportPayableParams, VendorRefParams, YardiRecordList, YardiRecord,
    DelinquencyReportParams, DelinquencyReport, DelinquentResident,
)

_INTERFACE = "billing_and_payments"


def _list_result(operation: str, data: object) -> YardiRecordList:
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict) and data:
        vals = list(data.values())
        records = vals[0] if len(vals) == 1 and isinstance(vals[0], list) else [data]
    else:
        records = []
    return YardiRecordList(interface=_INTERFACE, operation=operation, records=records, record_count=len(records))


@chat.function(
    "list_yardi_resident_transactions",
    "List resident ledger transactions (charges/payments) for a Yardi property, optionally in a date range.",
    action_type="read", chain_callable=True, data_model=YardiRecordList,
)
async def list_yardi_resident_transactions(ctx, params: ResidentTransactionsParams) -> ActionResult:
    """List resident ledger transactions (charges/payments) for a Yardi property, optionally in a date range."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "GetResidentTransactions_ByChargeDate_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {
            "YardiPropertyId": params.yardi_property_id,
            "FromDate": params.from_date,
            "ToDate": params.to_date,
        })
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not list resident transactions."))
    result = _list_result(op, data)
    return ActionResult.success(data=result, summary=f"{result.record_count} transaction(s) for property {params.yardi_property_id}.")


@chat.function(
    "import_yardi_charge",
    "Post a new charge to a resident's ledger in Yardi (e.g. a late fee or one-time charge).",
    action_type="write", chain_callable=True, data_model=YardiRecord,
    effects=["create:charge"], event="yardi-connector.import_yardi_charge",
)
async def import_yardi_charge(ctx, params: ImportChargeParams) -> ActionResult:
    """Post a new charge to a resident's ledger in Yardi (e.g. a late fee or one-time charge)."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "ImportCharge_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {
            "YardiPropertyId": params.yardi_property_id,
            "TenantCode": params.tenant_code,
            "ChargeCode": params.charge_code,
            "Amount": params.amount,
            "ChargeDate": params.charge_date,
            "Memo": params.memo,
        })
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not import the charge."))
    return ActionResult.success(
        data=YardiRecord(interface=_INTERFACE, operation=op, record=data if isinstance(data, dict) else {"value": data}),
        summary=f"Posted a {params.amount} charge ({params.charge_code}) to resident {params.tenant_code}.",
    )


@chat.function(
    "import_yardi_receipt",
    "Record a payment received from a resident in Yardi.",
    action_type="write", chain_callable=True, data_model=YardiRecord,
    effects=["create:payment"], event="yardi-connector.import_yardi_receipt",
)
async def import_yardi_receipt(ctx, params: ImportReceiptParams) -> ActionResult:
    """Record a payment received from a resident in Yardi."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "ImportReceipt_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {
            "YardiPropertyId": params.yardi_property_id,
            "TenantCode": params.tenant_code,
            "Amount": params.amount,
            "ReceiptDate": params.receipt_date,
            "PaymentType": params.payment_type,
        })
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not import the receipt."))
    return ActionResult.success(
        data=YardiRecord(interface=_INTERFACE, operation=op, record=data if isinstance(data, dict) else {"value": data}),
        summary=f"Recorded a {params.amount} payment from resident {params.tenant_code}.",
    )


@chat.function(
    "import_yardi_payable",
    "Post a vendor payable (an amount owed to a vendor) in Yardi.",
    action_type="write", chain_callable=True, data_model=YardiRecord,
    effects=["create:payable"], event="yardi-connector.import_yardi_payable",
)
async def import_yardi_payable(ctx, params: ImportPayableParams) -> ActionResult:
    """Post a vendor payable (an amount owed to a vendor) in Yardi."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "ImportPayables_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {
            "YardiPropertyId": params.yardi_property_id,
            "VendorCode": params.vendor_code,
            "Amount": params.amount,
            "InvoiceDate": params.invoice_date,
            "InvoiceNumber": params.invoice_number,
            "GLAccount": params.gl_account,
            "Memo": params.memo,
        })
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not import the payable."))
    return ActionResult.success(
        data=YardiRecord(interface=_INTERFACE, operation=op, record=data if isinstance(data, dict) else {"value": data}),
        summary=f"Posted a {params.amount} payable to vendor {params.vendor_code}.",
    )


@chat.function(
    "get_yardi_vendor",
    "Look up a vendor's own record on this Yardi Billing & Payments interface.",
    action_type="read", chain_callable=True, data_model=YardiRecord,
)
async def get_yardi_vendor(ctx, params: VendorRefParams) -> ActionResult:
    """Look up a vendor's own record on this Yardi Billing & Payments interface."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "GetVendors_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {"VendorCode": params.vendor_code})
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not get the vendor."))
    return ActionResult.success(
        data=YardiRecord(interface=_INTERFACE, operation=op, record=data if isinstance(data, dict) else {"value": data}),
        summary=f"Fetched vendor {params.vendor_code or '(all)'}.",
    )


def _to_float(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


@chat.function(
    "get_yardi_delinquency_report",
    "Value-add report: scan a property's resident transactions and build a delinquency list -- residents with a positive outstanding balance, sorted by amount owed. Not a native Yardi operation; built from GetResidentTransactions_ByChargeDate_Login.",
    action_type="read", chain_callable=True, data_model=DelinquencyReport,
)
async def get_yardi_delinquency_report(ctx, params: DelinquencyReportParams) -> ActionResult:
    """Value-add report: scan a property's resident transactions and build a delinquency list of residents with a positive outstanding balance."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    as_of = params.as_of_date or date.today().isoformat()
    try:
        data = await yc.call_operation(ctx, conn, "GetResidentTransactions_ByChargeDate_Login", {
            "YardiPropertyId": params.yardi_property_id,
            "FromDate": "",
            "ToDate": as_of,
        })
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not build the delinquency report."))

    records = data if isinstance(data, list) else (list(data.values())[0] if isinstance(data, dict) and len(data) == 1 and isinstance(list(data.values())[0], list) else [data] if data else [])

    balances: dict[str, dict] = {}
    for rec in records:
        if not isinstance(rec, dict):
            continue
        code = str(rec.get("TenantCode") or rec.get("Code") or "")
        if not code:
            continue
        name = str(rec.get("TenantName") or rec.get("Name") or code)
        amount = _to_float(rec.get("Amount") or rec.get("Charge") or 0)
        entry = balances.setdefault(code, {"name": name, "balance": 0.0})
        entry["balance"] += amount

    residents = [
        DelinquentResident(tenant_code=code, resident_name=v["name"], balance_due=round(v["balance"], 2), days_late=0)
        for code, v in balances.items() if v["balance"] > 0
    ]
    residents.sort(key=lambda r: r.balance_due, reverse=True)
    total = round(sum(r.balance_due for r in residents), 2)

    report = DelinquencyReport(
        yardi_property_id=params.yardi_property_id,
        as_of_date=as_of,
        total_balance_due=total,
        residents=residents,
    )
    return ActionResult.success(
        data=report,
        summary=f"{len(residents)} resident(s) with a balance due, totaling {total} as of {as_of}.",
    )
