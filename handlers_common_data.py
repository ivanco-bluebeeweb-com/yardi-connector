"""Common Data interface handlers -- properties, units, residents, leases,
documents, rent roll. Curated Tier 1+2 wrappers over yardi_client.call_operation,
using the exact operation/parameter names from yardi-sdk's endpoints/common_data.py
(CONNECTOR_DISCOVERY.md SS3).
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import yardi_client as yc
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    ListPropertiesParams, PropertyRefParams, DateRangeParams,
    ResidentRefParams, UnitInfoParams, ImportContactsParams,
    RentrollParams, LeaseInfoParams, YardiRecordList, YardiRecord,
)

_INTERFACE = "common_data"


def _list_result(operation: str, data: object) -> YardiRecordList:
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict) and data:
        # Yardi often wraps a single repeated element under one key --
        # normalize {"Property": [...]} or {"Property": {...}} to a flat list.
        vals = list(data.values())
        records = vals[0] if len(vals) == 1 and isinstance(vals[0], list) else [data]
    else:
        records = []
    return YardiRecordList(interface=_INTERFACE, operation=operation, records=records, record_count=len(records))


@chat.function(
    "list_yardi_properties",
    "List properties visible to this Yardi Common Data interface connection.",
    action_type="read", chain_callable=True, data_model=YardiRecordList,
)
async def list_yardi_properties(ctx, params: ListPropertiesParams) -> ActionResult:
    """List properties visible to this Yardi Common Data interface connection."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    try:
        data = await yc.call_operation(ctx, conn, "GetPropertyList", {})
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not list properties."))
    result = _list_result("GetPropertyList", data)
    return ActionResult.success(data=result, summary=f"{result.record_count} property record(s) found.")


@chat.function(
    "get_yardi_unit_information",
    "Read unit-level information (unit types, status, rent) for a Yardi property.",
    action_type="read", chain_callable=True, data_model=YardiRecordList,
)
async def get_yardi_unit_information(ctx, params: UnitInfoParams) -> ActionResult:
    """Read unit-level information (unit types, status, rent) for a Yardi property."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    try:
        data = await yc.call_operation(ctx, conn, "GetUnitInformation", {"YardiPropertyId": params.yardi_property_id})
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not get unit information."))
    result = _list_result("GetUnitInformation", data)
    return ActionResult.success(data=result, summary=f"{result.record_count} unit record(s) for property {params.yardi_property_id}.")


@chat.function(
    "list_yardi_residents",
    "List current residents/tenants for a Yardi property.",
    action_type="read", chain_callable=True, data_model=YardiRecordList,
)
async def list_yardi_residents(ctx, params: PropertyRefParams) -> ActionResult:
    """List current residents/tenants for a Yardi property."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    try:
        data = await yc.call_operation(ctx, conn, "GetResidents", {"YardiPropertyId": params.yardi_property_id})
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not list residents."))
    result = _list_result("GetResidents", data)
    return ActionResult.success(data=result, summary=f"{result.record_count} resident(s) at property {params.yardi_property_id}.")


@chat.function(
    "get_yardi_resident_info",
    "Read one resident/tenant's full record by property and tenant code.",
    action_type="read", chain_callable=True, data_model=YardiRecord,
)
async def get_yardi_resident_info(ctx, params: ResidentRefParams) -> ActionResult:
    """Read one resident/tenant's full record by property and tenant code."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    try:
        data = await yc.call_operation(ctx, conn, "GetResidentInformation", {
            "YardiPropertyId": params.yardi_property_id,
            "TenantCode": params.tenant_code,
        })
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not get resident information."))
    return ActionResult.success(
        data=YardiRecord(interface=_INTERFACE, operation="GetResidentInformation", record=data if isinstance(data, dict) else {"value": data}),
        summary=f"Fetched resident information for tenant {params.tenant_code} at property {params.yardi_property_id}.",
    )


@chat.function(
    "list_yardi_rentroll",
    "Read a property's rent roll (units, occupancy, rent amounts) as of a given date.",
    action_type="read", chain_callable=True, data_model=YardiRecordList,
)
async def list_yardi_rentroll(ctx, params: RentrollParams) -> ActionResult:
    """Read a property's rent roll (units, occupancy, rent amounts) as of a given date."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    try:
        data = await yc.call_operation(ctx, conn, "GetRentroll", {
            "YardiPropertyId": params.yardi_property_id,
            "AsOfDate": params.as_of_date,
        })
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not get rent roll."))
    result = _list_result("GetRentroll", data)
    return ActionResult.success(data=result, summary=f"Rent roll: {result.record_count} unit(s) for property {params.yardi_property_id}.")


@chat.function(
    "import_yardi_contacts",
    "Import a batch of contacts/prospects into this Yardi Common Data interface.",
    action_type="write", chain_callable=True, data_model=YardiRecord,
    effects=["create:contact"], event="yardi-connector.import_yardi_contacts",
)
async def import_yardi_contacts(ctx, params: ImportContactsParams) -> ActionResult:
    """Import a batch of contacts/prospects into this Yardi Common Data interface."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    import json
    try:
        payload = json.loads(params.contacts_json)
    except Exception as e:
        return ActionResult.error(f"contacts_json is not valid JSON: {e}")
    try:
        data = await yc.call_operation(ctx, conn, "ImportContacts_Login", {
            "YardiPropertyId": params.yardi_property_id,
            "Contacts": payload,
        })
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not import contacts."))
    return ActionResult.success(
        data=YardiRecord(interface=_INTERFACE, operation="ImportContacts_Login", record=data if isinstance(data, dict) else {"value": data}),
        summary=f"Imported contacts for property {params.yardi_property_id}.",
    )


@chat.function(
    "get_yardi_lease_information",
    "Read one tenant's lease information (term, rent, dates) by property and tenant code.",
    action_type="read", chain_callable=True, data_model=YardiRecord,
)
async def get_yardi_lease_information(ctx, params: LeaseInfoParams) -> ActionResult:
    """Read one tenant's lease information (term, rent, dates) by property and tenant code."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    try:
        data = await yc.call_operation(ctx, conn, "GetLeaseInformation", {"YardiPropertyId": params.yardi_property_id, "TenantCode": params.tenant_code})
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not get lease information."))
    return ActionResult.success(
        data=YardiRecord(interface=_INTERFACE, operation="GetLeaseInformation", record=data if isinstance(data, dict) else {"value": data}),
        summary=f"Fetched lease information for property {params.yardi_property_id}.",
    )
