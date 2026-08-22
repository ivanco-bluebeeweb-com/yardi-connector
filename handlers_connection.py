"""Chat functions for connection management: connect/disconnect/list saved
Yardi Voyager interface connections. Built on yardi_client.py / schemas.py,
same shape as Ironclad/Iguana/PagerDuty/MuleSoft Connector's connection
section.
"""
from __future__ import annotations

import json
import uuid

from imperal_sdk import ActionResult

import yardi_client as yc
from app import ext, chat
from schemas import (
    NoParams,
    ConnectYardiParams, ProviderConnection, ProviderConnectionList,
    DisconnectYardiParams, DeleteResult,
)

_SECRET_NAME = "yardi_connections"

_INTERFACE_LABELS = {
    "common_data": "Common Data",
    "billing_and_payments": "Billing & Payments",
    "vendor_invoicing": "Vendor Invoicing",
    "service_requests": "Service Requests",
    "revenue_management": "Revenue Management",
    "lease_renewals": "Lease Renewals",
    "ils_guest_card": "ILS/Guest Card",
}


async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_SECRET_NAME)
    try:
        return json.loads(raw) if raw else []
    except Exception:
        return []


async def _save_connections(ctx, connections: list[dict]) -> None:
    await ctx.secrets.set(_SECRET_NAME, json.dumps(connections))


def _to_provider_connection(c: dict) -> ProviderConnection:
    interface = c.get("interface", "common_data")
    label = _INTERFACE_LABELS.get(interface, interface)
    return ProviderConnection(
        id=c.get("id", ""),
        title=c.get("label") or f"Yardi \u2014 {label}",
        interface=interface,
        detail=f"{label} \u00b7 {c.get('ServerName', '')}/{c.get('Database', '')}",
    )


async def resolve_connection(ctx, connection_id: str = "", interface: str = ""):
    """Resolve a connection_id (or the first saved connection matching
    `interface` if given, else the first saved connection overall) to a
    conn dict. Returns an ActionResult.error(...) instead if none match --
    callers must check `isinstance(result, ActionResult)`."""
    connections = await _load_connections(ctx)
    if not connections:
        return ActionResult.error(
            "No Yardi connection saved yet. Use connect_yardi first."
        )
    if connection_id:
        for c in connections:
            if c.get("id") == connection_id:
                return c
        return ActionResult.error(f"No saved Yardi connection with id '{connection_id}'.")
    if interface:
        for c in connections:
            if c.get("interface") == interface:
                return c
        label = _INTERFACE_LABELS.get(interface, interface)
        return ActionResult.error(
            f"No saved Yardi connection for the {label} interface. Use connect_yardi with interface='{interface}' first."
        )
    return connections[0]


@chat.function(
    "connect_yardi",
    "Connect one of your own Yardi Voyager Standard Interfaces (Common "
    "Data, Billing & Payments, Vendor Invoicing, Service Requests, "
    "Revenue Management, Lease Renewals, or ILS/Guest Card) by saving its "
    "WSDL URL and Login-block credentials, after checking it actually "
    "works.",
    action_type="write",
    chain_callable=True,
    data_model=ProviderConnection,
    event="yardi-connector.connect_yardi",
    effects=["create:connection"],
)
async def connect_yardi(ctx, params: ConnectYardiParams) -> ActionResult:
    """Verify and save a new Yardi Voyager interface connection."""
    interface = (params.interface or "common_data").strip().lower()
    if interface not in _INTERFACE_LABELS:
        return ActionResult.error(
            f"Unknown interface '{params.interface}'. Use one of: "
            + ", ".join(_INTERFACE_LABELS.keys())
        )
    if not params.wsdl_url:
        return ActionResult.error("wsdl_url is required.")

    entry = {
        "id": str(uuid.uuid4()),
        "wsdl_url": params.wsdl_url,
        "interface": interface,
        "UserName": params.username,
        "Password": params.password,
        "ServerName": params.server_name,
        "Database": params.database,
        "Platform": params.platform,
        "InterfaceEntity": params.interface_entity,
        "InterfaceLicense": params.interface_license,
        "label": params.label,
    }
    check = await yc.check_connection(ctx, entry)
    if not check.get("ok"):
        return ActionResult.error(check.get("error", "Could not verify the Yardi connection."))

    connections = await _load_connections(ctx)
    connections.append(entry)
    await _save_connections(ctx, connections)
    conn = _to_provider_connection(entry)
    return ActionResult.success(
        data=conn,
        summary=f"Connected Yardi {_INTERFACE_LABELS[interface]} interface.",
        refresh_panels=["yardi_sidebar", "yardi_settings"],
    )


@chat.function(
    "list_connections",
    "List your saved Yardi Voyager interface connections.",
    action_type="read",
    chain_callable=True,
    data_model=ProviderConnectionList,
)
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """List your saved Yardi Voyager interface connections."""
    connections = await _load_connections(ctx)
    items = [_to_provider_connection(c) for c in connections]
    return ActionResult.success(
        data=ProviderConnectionList(connections=items),
        summary=f"{len(items)} Yardi connection(s) saved.",
    )


@chat.function(
    "disconnect_yardi",
    "Disconnect a saved Yardi Voyager interface connection: deletes the "
    "saved WSDL URL and credentials. Nothing in Yardi itself is changed.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="yardi-connector.disconnect_yardi",
    effects=["delete:connection"],
)
async def disconnect_yardi(ctx, params: DisconnectYardiParams) -> ActionResult:
    """Disconnect a saved Yardi Voyager interface connection: deletes the saved WSDL URL and credentials."""
    connections = await _load_connections(ctx)
    remaining = [c for c in connections if c.get("id") != params.connection_id]
    if len(remaining) == len(connections):
        return ActionResult.error(f"No saved Yardi connection with id '{params.connection_id}'.")
    await _save_connections(ctx, remaining)
    return ActionResult.success(
        data=DeleteResult(deleted=True, id=params.connection_id),
        summary="Yardi connection disconnected.",
        refresh_panels=["yardi_sidebar", "yardi_settings"],
    )
