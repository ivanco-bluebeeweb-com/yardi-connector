"""Lease Renewals interface handlers -- scheduled renewals, generated
lease offers, and importing a resident's renewal selection.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import yardi_client as yc
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    ScheduledRenewalsParams, LeaseOffersParams, ImportRenewalSelectionParams,
    YardiRecordList, YardiRecord,
)

_INTERFACE = "lease_renewals"


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
    "list_yardi_scheduled_renewals",
    "List leases scheduled for renewal at a Yardi property.",
    action_type="read", chain_callable=True, data_model=YardiRecordList,
)
async def list_yardi_scheduled_renewals(ctx, params: ScheduledRenewalsParams) -> ActionResult:
    """List leases scheduled for renewal at a Yardi property."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "GetScheduledRenewals_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {"YardiPropertyId": params.yardi_property_id})
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not list scheduled renewals."))
    result = _list_result(op, data)
    return ActionResult.success(data=result, summary=f"{result.record_count} scheduled renewal(s) for property {params.yardi_property_id}.")


@chat.function(
    "list_yardi_lease_offers",
    "List generated lease renewal offers, optionally scoped to one property.",
    action_type="read", chain_callable=True, data_model=YardiRecordList,
)
async def list_yardi_lease_offers(ctx, params: LeaseOffersParams) -> ActionResult:
    """List generated lease renewal offers, optionally scoped to one property."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "GetLeaseOffers_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {"YardiPropertyId": params.yardi_property_id})
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not list lease offers."))
    result = _list_result(op, data)
    return ActionResult.success(data=result, summary=f"{result.record_count} lease offer(s).")


@chat.function(
    "import_yardi_renewal_selection",
    "Record a resident's selected lease renewal offer in Yardi.",
    action_type="write", chain_callable=True, data_model=YardiRecord,
    effects=["update:lease"], event="yardi-connector.import_yardi_renewal_selection",
)
async def import_yardi_renewal_selection(ctx, params: ImportRenewalSelectionParams) -> ActionResult:
    """Record a resident's selected lease renewal offer in Yardi."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "ImportRenewalSelection_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {
            "YardiPropertyId": params.yardi_property_id,
            "TenantCode": params.tenant_code,
            "SelectedOfferId": params.selected_offer_id,
            "NewLeaseStart": params.new_lease_start,
            "NewLeaseEnd": params.new_lease_end,
        })
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not import the renewal selection."))
    return ActionResult.success(
        data=YardiRecord(interface=_INTERFACE, operation=op, record=data if isinstance(data, dict) else {"value": data}),
        summary=f"Recorded renewal selection for resident {params.tenant_code}.",
    )
