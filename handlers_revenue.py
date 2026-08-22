"""Revenue Management interface handlers -- read revenue-management data
per property, and push unit-level rent/pricing updates.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import yardi_client as yc
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import RevenuePropertyParams, ImportRevenueParams, YardiRecord
import json


_INTERFACE = "revenue_management"


@chat.function(
    "get_yardi_revenue_data",
    "Read revenue management data (pricing/availability recommendations) for a Yardi property.",
    action_type="read", chain_callable=True, data_model=YardiRecord,
)
async def get_yardi_revenue_data(ctx, params: RevenuePropertyParams) -> ActionResult:
    """Read revenue management data (pricing/availability recommendations) for a Yardi property."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "GetRevenueManagementData_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {"YardiPropertyId": params.yardi_property_id})
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not get revenue management data."))
    return ActionResult.success(
        data=YardiRecord(interface=_INTERFACE, operation=op, record=data if isinstance(data, dict) else {"value": data}),
        summary=f"Fetched revenue management data for property {params.yardi_property_id}.",
    )


@chat.function(
    "import_yardi_revenue_update",
    "Push a unit-level rent/pricing update into Yardi Revenue Management.",
    action_type="write", chain_callable=True, data_model=YardiRecord,
    effects=["update:pricing"], event="yardi-connector.import_yardi_revenue_update",
)
async def import_yardi_revenue_update(ctx, params: ImportRevenueParams) -> ActionResult:
    """Push a unit-level rent/pricing update into Yardi Revenue Management."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    try:
        payload = json.loads(params.payload_json)
    except Exception as e:
        return ActionResult.error(f"payload_json is not valid JSON: {e}")
    if not isinstance(payload, dict):
        return ActionResult.error("payload_json must be a JSON object.")
    op = "ImportRM_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {"YardiPropertyId": params.yardi_property_id, **payload})
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not import the revenue update."))
    return ActionResult.success(
        data=YardiRecord(interface=_INTERFACE, operation=op, record=data if isinstance(data, dict) else {"value": data}),
        summary=f"Imported revenue update for property {params.yardi_property_id}.",
    )
