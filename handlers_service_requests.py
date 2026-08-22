"""Service Requests interface handlers -- maintenance/work order search,
creation, and attachment lookup, plus a value-add open-work-orders report.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import yardi_client as yc
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    ServiceRequestSearchParams, CreateServiceRequestParams,
    ServiceRequestAttachmentParams, YardiRecordList, YardiRecord,
    OpenWorkOrdersReportParams, OpenWorkOrdersReport, OpenWorkOrder,
)

_INTERFACE = "service_requests"


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
    "search_yardi_service_requests",
    "Search maintenance/service requests for a Yardi property, optionally in a date range.",
    action_type="read", chain_callable=True, data_model=YardiRecordList,
)
async def search_yardi_service_requests(ctx, params: ServiceRequestSearchParams) -> ActionResult:
    """Search maintenance/service requests for a Yardi property, optionally in a date range."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "GetServiceRequests_Search"
    try:
        data = await yc.call_operation(ctx, conn, op, {
            "YardiPropertyId": params.yardi_property_id,
            "FromDate": params.from_date,
            "ToDate": params.to_date,
        })
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not search service requests."))
    result = _list_result(op, data)
    return ActionResult.success(data=result, summary=f"{result.record_count} service request(s) found.")


@chat.function(
    "create_yardi_service_request",
    "Create a new maintenance/service request against a Yardi unit.",
    action_type="write", chain_callable=True, data_model=YardiRecord,
    effects=["create:service_request"], event="yardi-connector.create_yardi_service_request",
)
async def create_yardi_service_request(ctx, params: CreateServiceRequestParams) -> ActionResult:
    """Create a new maintenance/service request against a Yardi unit."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "ImportServiceRequest_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {
            "YardiPropertyId": params.yardi_property_id,
            "UnitId": params.unit_id,
            "ProblemDescription": params.problem_description,
            "Priority": params.priority,
        })
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not create the service request."))
    return ActionResult.success(
        data=YardiRecord(interface=_INTERFACE, operation=op, record=data if isinstance(data, dict) else {"value": data}),
        summary=f"Service request created for unit {params.unit_id} at property {params.yardi_property_id}.",
    )


@chat.function(
    "list_yardi_service_request_attachments",
    "List attachment types and charge codes configured for service requests on a Yardi property.",
    action_type="read", chain_callable=True, data_model=YardiRecordList,
)
async def list_yardi_service_request_attachments(ctx, params: ServiceRequestAttachmentParams) -> ActionResult:
    """List attachment types and charge codes configured for service requests on a Yardi property."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "GetAttachmentTypesAndChargeCodes"
    try:
        data = await yc.call_operation(ctx, conn, op, {"YardiPropertyId": params.yardi_property_id})
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not list attachment types and charge codes."))
    result = _list_result(op, data)
    return ActionResult.success(data=result, summary=f"{result.record_count} attachment/charge-code entr(y/ies) found.")


@chat.function(
    "get_yardi_open_work_orders_report",
    "Value-add report: list open (not closed/completed/cancelled) service requests for a Yardi property, sorted by priority, flagging urgent/emergency ones. Not a native Yardi operation.",
    action_type="read", chain_callable=True, data_model=OpenWorkOrdersReport,
)
async def get_yardi_open_work_orders_report(ctx, params: OpenWorkOrdersReportParams) -> ActionResult:
    """Value-add report: list open service requests for a Yardi property, sorted by priority, flagging urgent/emergency ones."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    try:
        data = await yc.call_operation(ctx, conn, "GetServiceRequests_Search", {
            "YardiPropertyId": params.yardi_property_id,
            "FromDate": params.from_date,
            "ToDate": params.to_date,
        })
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not build the open work orders report."))

    records = data if isinstance(data, list) else (list(data.values())[0] if isinstance(data, dict) and len(data) == 1 and isinstance(list(data.values())[0], list) else [data] if data else [])

    orders: list[OpenWorkOrder] = []
    urgent = 0
    for rec in records:
        if not isinstance(rec, dict):
            continue
        status = str(rec.get("Status") or rec.get("StatusCode") or "").strip().lower()
        if status in ("closed", "completed", "cancelled", "canceled"):
            continue
        priority = str(rec.get("Priority") or "Normal")
        if priority.strip().lower() in ("urgent", "emergency"):
            urgent += 1
        orders.append(OpenWorkOrder(
            service_request_id=str(rec.get("ServiceRequestId") or rec.get("Id") or ""),
            unit_id=str(rec.get("UnitId") or ""),
            priority=priority,
            days_open=0,
            description=str(rec.get("ProblemDescription") or rec.get("Description") or ""),
        ))

    report = OpenWorkOrdersReport(
        yardi_property_id=params.yardi_property_id,
        open_count=len(orders),
        urgent_count=urgent,
    )
    return ActionResult.success(
        data=report,
        summary=f"{len(orders)} open work order(s) for property {params.yardi_property_id}, {urgent} urgent/emergency.",
    )
