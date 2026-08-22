"""The single "App settings" screen (center slot) -- connection management
(disconnect per Yardi interface connection) for Yardi Connector. Split out
of panels.py per the same convention as Iguana/GitLab CI/CD/MuleSoft
Connector's panels_settings.py.

Per ~/UI_INTERFACE_STANDARD.md: the left sidebar never wraps the connect
form in a Card, and disconnect (never exposed in the sidebar itself) lives
here, one row per connected interface. The one secondary "App settings"
button sits LAST at the bottom of the sidebar. The help modal (its own
separate panel, opened from this screen) is the ONLY place carrying the
BYOK/per-interface-licensing explanation -- the sidebar never repeats it.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
from handlers_connection import _load_connections, _INTERFACE_LABELS


def _connection_row(c: dict) -> ui.UINode:
    interface = c.get("interface", "common_data")
    label = c.get("label") or f"Yardi — {_INTERFACE_LABELS.get(interface, interface)}"
    detail = f"{_INTERFACE_LABELS.get(interface, interface)} · {c.get('ServerName', '')}/{c.get('Database', '')}"
    return ui.Stack(direction="v", gap=1, align="start", children=[
        ui.Text(label, variant="body"),
        ui.Text(detail, variant="caption"),
        ui.Button(
            "Disconnect", variant="danger", size="sm",
            on_click=ui.Call("disconnect_yardi", {"connection_id": c.get("id")}),
        ),
    ])


def _connections_section(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Stack(direction="v", gap=1, children=[
            ui.Text("Yardi interface connections", variant="heading"),
            ui.Text("No Yardi interfaces connected yet.", variant="caption"),
        ])
    children: list[ui.UINode] = [ui.Text("Yardi interface connections", variant="heading")]
    for i, c in enumerate(connections):
        if i:
            children.append(ui.Divider())
        children.append(_connection_row(c))
    return ui.Stack(direction="v", gap=2, children=children)


@ext.panel("yardi_settings", slot="center", title="Yardi — App settings", center_overlay=True)
async def yardi_settings_panel(ctx, **kwargs) -> ui.UINode:
    connections = await _load_connections(ctx)
    return ui.Stack(direction="v", gap=4, align="stretch", children=[
        ui.Header(text="App settings", level=2, subtitle="Yardi Connector"),
        _connections_section(connections),
        ui.Divider(),
        ui.Button(
            "About this connector", variant="ghost", size="sm",
            on_click=ui.Call("__panel__yardi_help"),
        ),
    ])


@ext.panel("yardi_help", slot="center", title="About Yardi Connector", center_overlay=True)
async def yardi_help_panel(ctx, **kwargs) -> ui.UINode:
    """The one place carrying the BYOK/licensing explanation -- never
    duplicated in the sidebar. See app.py's module docstring and
    CONNECTOR_DISCOVERY.md SS1-2 for the full citation trail behind this
    text."""
    content = ui.Stack(direction="v", gap=3, children=[
        ui.Text(
            "This connector talks directly to YOUR OWN Yardi Voyager "
            "instance over SOAP -- Imperal never brokers access to "
            "someone else's leasing, billing, or maintenance data "
            "centrally. You supply the WSDL URL and Login-block "
            "credentials Yardi itself requires for each interface."
        ),
        ui.Divider(),
        ui.Text(
            "Yardi licenses its 7 Standard Interfaces (Common Data, "
            "Billing & Payments, Vendor Invoicing, Service Requests, "
            "Revenue Management, Lease Renewals, ILS/Guest Card) "
            "separately, each as its own hosted SOAP service with its "
            "own InterfaceLicense key. That's why each connection here "
            "is scoped to ONE interface -- connect only the ones your "
            "organization has actually licensed."
        ),
        ui.Divider(),
        ui.Text(
            "Your UserName, Password, ServerName, Database, Platform, "
            "InterfaceEntity, and InterfaceLicense values are sent "
            "inside the SOAP Login block on every call, exactly as "
            "Yardi's own web services expect -- there is no separate "
            "OAuth or API-key login step."
        ),
        ui.Divider(),
        ui.Text(
            "Yardi publishes no public specification for these "
            "interfaces, so this connector introspects each WSDL live "
            "to resolve the correct operation and SOAP action -- if an "
            "operation your Voyager deployment doesn't expose is "
            "called, you'll get a clear error rather than a silent "
            "failure."
        ),
    ])
    return ui.Dialog(
        title="About this connector",
        content=content,
        confirm_label="",
        cancel_label="Close",
    )
