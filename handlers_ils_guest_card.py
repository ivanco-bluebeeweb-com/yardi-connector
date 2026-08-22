"""ILS/Guest Card interface handlers -- unit availability, guest card
(prospect) import, guest activity search, and rental applications.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import yardi_client as yc
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    AvailableUnitsParams, ImportGuestCardParams, GuestActivitySearchParams,
    ApplicationParams, ImportApplicationParams, YardiRecordList, YardiRecord,
)

_INTERFACE = "ils_guest_card"


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
    "list_yardi_available_units",
    "List units currently available for lease at a Yardi property (ILS/Guest Card interface).",
    action_type="read", chain_callable=True, data_model=YardiRecordList,
)
async def list_yardi_available_units(ctx, params: AvailableUnitsParams) -> ActionResult:
    """List units currently available for lease at a Yardi property (ILS/Guest Card interface)."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "AvailableUnits_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {"YardiPropertyId": params.yardi_property_id})
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not list available units."))
    result = _list_result(op, data)
    return ActionResult.success(data=result, summary=f"{result.record_count} available unit(s) at property {params.yardi_property_id}.")


@chat.function(
    "import_yardi_guest_card",
    "Import a new prospect (guest card) into Yardi's ILS pipeline -- e.g. from a website lead form.",
    action_type="write", chain_callable=True, data_model=YardiRecord,
    effects=["create:prospect"], event="yardi-connector.import_yardi_guest_card",
)
async def import_yardi_guest_card(ctx, params: ImportGuestCardParams) -> ActionResult:
    """Import a new prospect (guest card) into Yardi's ILS pipeline -- e.g. from a website lead form."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "ImportYardiGuest_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {
            "YardiPropertyId": params.yardi_property_id,
            "FirstName": params.first_name,
            "LastName": params.last_name,
            "Email": params.email,
            "Phone": params.phone,
            "Source": params.source,
            "DesiredMoveIn": params.desired_move_in,
            "Notes": params.notes,
        })
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not import the guest card."))
    return ActionResult.success(
        data=YardiRecord(interface=_INTERFACE, operation=op, record=data if isinstance(data, dict) else {"value": data}),
        summary=f"Imported guest card for {params.first_name} {params.last_name} at property {params.yardi_property_id}.",
    )


@chat.function(
    "search_yardi_guest_activity",
    "Search prospect/guest activity (tours, follow-ups) for a Yardi property, optionally in a date range.",
    action_type="read", chain_callable=True, data_model=YardiRecordList,
)
async def search_yardi_guest_activity(ctx, params: GuestActivitySearchParams) -> ActionResult:
    """Search prospect/guest activity (tours, follow-ups) for a Yardi property, optionally in a date range."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "GetYardiGuestActivity_DateRange"
    try:
        data = await yc.call_operation(ctx, conn, op, {
            "YardiPropertyId": params.yardi_property_id,
            "FromDate": params.from_date,
            "ToDate": params.to_date,
        })
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not search guest activity."))
    result = _list_result(op, data)
    return ActionResult.success(data=result, summary=f"{result.record_count} guest activity record(s).")


@chat.function(
    "get_yardi_application",
    "Read one rental application in full from Yardi ILS/Guest Card.",
    action_type="read", chain_callable=True, data_model=YardiRecord,
)
async def get_yardi_application(ctx, params: ApplicationParams) -> ActionResult:
    """Read one rental application in full from Yardi ILS/Guest Card."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "GetApplication_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {"ApplicationId": params.application_id})
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not get the application."))
    return ActionResult.success(
        data=YardiRecord(interface=_INTERFACE, operation=op, record=data if isinstance(data, dict) else {"value": data}),
        summary=f"Fetched application {params.application_id}.",
    )


@chat.function(
    "import_yardi_application",
    "Submit a new rental application into Yardi ILS/Guest Card for a specific unit.",
    action_type="write", chain_callable=True, data_model=YardiRecord,
    effects=["create:application"], event="yardi-connector.import_yardi_application",
)
async def import_yardi_application(ctx, params: ImportApplicationParams) -> ActionResult:
    """Submit a new rental application into Yardi ILS/Guest Card for a specific unit."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    op = "ImportApplication_Login"
    try:
        data = await yc.call_operation(ctx, conn, op, {
            "YardiPropertyId": params.yardi_property_id,
            "UnitId": params.unit_id,
            "FirstName": params.first_name,
            "LastName": params.last_name,
            "Email": params.email,
            "DesiredMoveIn": params.desired_move_in,
        })
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not import the application."))
    return ActionResult.success(
        data=YardiRecord(interface=_INTERFACE, operation=op, record=data if isinstance(data, dict) else {"value": data}),
        summary=f"Submitted application for {params.first_name} {params.last_name}, unit {params.unit_id}.",
    )
