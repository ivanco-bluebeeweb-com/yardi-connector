"""Universal SOAP passthrough (Tier 3) -- call ANY operation on ANY
connected Yardi interface by exact name, plus a WSDL introspection
listing so a user/agent can discover what's actually available on their
own Voyager deployment (yardi-sdk's endpoint list is a reference, not a
guarantee -- every client's licensed operation set can differ).
"""
from __future__ import annotations

import json

from imperal_sdk import ActionResult

import yardi_client as yc
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    CallYardiOperationParams, YardiOperationResult,
    ListWsdlOperationsParams, WsdlOperationList, WsdlOperation,
)


@chat.function(
    "call_yardi_operation",
    "Call ANY SOAP operation on a connected Yardi interface by its exact name (e.g. GetResidents, ImportCharge_Login, GetPurchaseOrders) -- full coverage beyond the curated wrapper functions, for operations not yet given their own dedicated tool.",
    action_type="write", chain_callable=True, data_model=YardiOperationResult,
    effects=["external:soap_call"], event="yardi-connector.call_yardi_operation",
)
async def call_yardi_operation(ctx, params: CallYardiOperationParams) -> ActionResult:
    """Call ANY SOAP operation on a connected Yardi interface by its exact name -- full coverage beyond the curated wrapper functions."""
    conn = await resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        op_params = json.loads(params.parameters_json or "{}")
    except Exception as e:
        return ActionResult.error(f"parameters_json is not valid JSON: {e}")
    if not isinstance(op_params, dict):
        return ActionResult.error("parameters_json must be a JSON object.")

    try:
        data = await yc.call_operation(ctx, conn, params.operation, op_params)
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", f"Could not call {params.operation}."))

    parsed = data if isinstance(data, dict) else {"value": data}
    result = YardiOperationResult(operation=params.operation, raw_xml="", parsed=parsed)
    return ActionResult.success(data=result, summary=f"Called {params.operation}.")


@chat.function(
    "list_yardi_wsdl_operations",
    "Introspect a connected Yardi interface's own WSDL and list every SOAP operation it actually exposes -- use this to discover exact operation names before calling call_yardi_operation, since licensed operation sets can differ between Voyager deployments.",
    action_type="read", chain_callable=True, data_model=WsdlOperationList,
)
async def list_yardi_wsdl_operations(ctx, params: ListWsdlOperationsParams) -> ActionResult:
    """Introspect a connected Yardi interface's own WSDL and list every SOAP operation it actually exposes."""
    conn = await resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        target_ns, ops = await yc.list_wsdl_operations(ctx, conn["wsdl_url"])
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not introspect the WSDL."))
    operations = [WsdlOperation(name=name, soap_action=action) for name, action in ops]
    result = WsdlOperationList(target_namespace=target_ns, operations=operations)
    return ActionResult.success(data=result, summary=f"{len(operations)} operation(s) found on this WSDL.")
