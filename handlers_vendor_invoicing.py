"""Vendor Invoicing interface handlers -- invoice register, purchase
orders, job cost, budget reads.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import yardi_client as yc
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    InvoiceRegisterParams, ImportInvoiceRegisterParams, PurchaseOrderParams,
    ImportPurchaseOrderParams, JobCostParams, BudgetParams,
    YardiRecordList, YardiRecord,
)

_INTERFACE = "vendor_invoicing"


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
    "list_yardi_invoice_register",
    "List vendor invoices recorded in Yardi's invoice register, optionally scoped to one property and date range.",
    action_type="read", chain_callable=True, data_model=YardiRecordList,
)
async def list_yardi_invoice_register(ctx, params: InvoiceRegisterParams) -> ActionResult:
    """List vendor invoices recorded in Yardi's invoice register, optionally scoped to one property and date range."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "GetInvoiceRegister_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {
            "YardiPropertyId": params.yardi_property_id,
            "FromDate": params.from_date,
            "ToDate": params.to_date,
        })
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not list the invoice register."))
    result = _list_result(op, data)
    return ActionResult.success(data=result, summary=f"{result.record_count} invoice(s) found.")


@chat.function(
    "import_yardi_invoice",
    "Post a new vendor invoice into Yardi's invoice register.",
    action_type="write", chain_callable=True, data_model=YardiRecord,
    effects=["create:invoice"], event="yardi-connector.import_yardi_invoice",
)
async def import_yardi_invoice(ctx, params: ImportInvoiceRegisterParams) -> ActionResult:
    """Post a new vendor invoice into Yardi's invoice register."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "ImportInvoiceRegister_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {
            "YardiPropertyId": params.yardi_property_id,
            "VendorCode": params.vendor_code,
            "InvoiceNumber": params.invoice_number,
            "InvoiceDate": params.invoice_date,
            "Amount": params.amount,
            "GLAccount": params.gl_account,
            "PurchaseOrderNumber": params.purchase_order_number,
        })
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not post the invoice."))
    return ActionResult.success(
        data=YardiRecord(interface=_INTERFACE, operation=op, record=data if isinstance(data, dict) else {"value": data}),
        summary=f"Invoice {params.invoice_number} posted for vendor {params.vendor_code} at property {params.yardi_property_id}.",
    )


@chat.function(
    "list_yardi_purchase_orders",
    "List purchase orders for a Yardi property, optionally filtered by modification date.",
    action_type="read", chain_callable=True, data_model=YardiRecordList,
)
async def list_yardi_purchase_orders(ctx, params: PurchaseOrderParams) -> ActionResult:
    """List purchase orders for a Yardi property, optionally filtered by modification date."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "GetPurchaseOrders_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {
            "YardiPropertyId": params.yardi_property_id,
            "FromDate": params.from_date,
        })
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not list purchase orders."))
    result = _list_result(op, data)
    return ActionResult.success(data=result, summary=f"{result.record_count} purchase order(s) found.")


@chat.function(
    "import_yardi_purchase_order",
    "Create a new purchase order in Yardi for a vendor.",
    action_type="write", chain_callable=True, data_model=YardiRecord,
    effects=["create:purchase_order"], event="yardi-connector.import_yardi_purchase_order",
)
async def import_yardi_purchase_order(ctx, params: ImportPurchaseOrderParams) -> ActionResult:
    """Create a new purchase order in Yardi for a vendor."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "ImportPurchaseOrder_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {
            "YardiPropertyId": params.yardi_property_id,
            "VendorCode": params.vendor_code,
            "Amount": params.amount,
            "Description": params.description,
            "GLAccount": params.gl_account,
        })
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not create the purchase order."))
    return ActionResult.success(
        data=YardiRecord(interface=_INTERFACE, operation=op, record=data if isinstance(data, dict) else {"value": data}),
        summary=f"Purchase order created for vendor {params.vendor_code} at property {params.yardi_property_id}.",
    )


@chat.function(
    "get_yardi_job_cost",
    "Read job cost data for a Yardi property (Vendor Invoicing interface).",
    action_type="read", chain_callable=True, data_model=YardiRecordList,
)
async def get_yardi_job_cost(ctx, params: JobCostParams) -> ActionResult:
    """Read job cost data for a Yardi property (Vendor Invoicing interface)."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "GetJobCost_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {"YardiPropertyId": params.yardi_property_id})
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not get job cost data."))
    result = _list_result(op, data)
    return ActionResult.success(data=result, summary=f"{result.record_count} job cost record(s) for property {params.yardi_property_id}.")


@chat.function(
    "get_yardi_budget",
    "Read budget data for a Yardi property, optionally for one specific month.",
    action_type="read", chain_callable=True, data_model=YardiRecordList,
)
async def get_yardi_budget(ctx, params: BudgetParams) -> ActionResult:
    """Read budget data for a Yardi property, optionally for one specific month."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "GetBudget_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {
            "YardiPropertyId": params.yardi_property_id,
            "Month": params.month,
        })
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not get budget data."))
    result = _list_result(op, data)
    return ActionResult.success(data=result, summary=f"{result.record_count} budget record(s) for property {params.yardi_property_id}.")
