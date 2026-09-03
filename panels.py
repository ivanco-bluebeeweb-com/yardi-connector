"""Panel UI -- connections list/connect form for Yardi Connector.

SIDEBAR CONTENT -- NO CARDS ANYWHERE, per ~/UI_INTERFACE_STANDARD.md's
"left sidebar, no decorated cards" rule (same convention as Iguana
Connector's / GitLab CI/CD Connector's panels.py).

Every section (connections summary, connect form) is a plain ui.Stack,
content stacked vertically and left-aligned, sections separated by
ui.Divider() -- no Card border/background/shadow anywhere in this slot.
Disconnect lives only in the "App settings" screen (panels_settings.py).
The one secondary "App settings" button is always the LAST element at
the bottom of the sidebar.

Per Vlad's standing rule: every input carries its own label (a ui.Text
caption above it, since ui.Input itself has no label kwarg), placeholders
are contextually specific, the form container is stretched to the full
width of the left sidebar with its contents stretched to fill it, and no
instructional text duplicates what already lives in the button's help
modal (see panels_settings.py's help modal).

ONE CONNECT FORM, NOT SEVEN -- the same credential SHAPE (WSDL URL +
Login block fields) applies to every one of Yardi's 7 Standard
Interfaces; the interface picker (a Select) is just one more field in
that single form, matching how ConnectYardiParams is structured (see
schemas.py / app.py's module docstring for the full "one connection per
interface" reasoning).
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
from handlers_connection import _load_connections, _INTERFACE_LABELS


def _settings_button() -> ui.UINode:
    """The one required secondary entry point into the settings screen --
    always the last element at the bottom of the sidebar."""
    return ui.Button("App settings", variant="secondary", size="sm",
                      on_click=ui.Call("__panel__yardi_settings"))


def _connect_form() -> ui.UINode:
    interface_options = [
        {"value": k, "label": v} for k, v in _INTERFACE_LABELS.items()
    ]
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Button("Sign in with Yardi (SSO / Voyager Auth)", variant="primary", size="sm", icon="login"),
        ui.Divider(),
        ui.Text("Or connect via Standard Interface WSDL / Web Services", variant="caption"),
        ui.Form(
            action="connect_yardi",
            submit_label="Connect interface",
            children=[
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Yardi Standard Interface", variant="caption"),
                    ui.Select(param_name="interface", options=interface_options,
                              placeholder="Which interface is this WSDL for?"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Interface WSDL URL", variant="caption"),
                    ui.Input(param_name="wsdl_url",
                             placeholder="https://www.yardiasp13.com/yourclient/webservices/ItfCommonData.asmx?WSDL"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Voyager UserName", variant="caption"),
                    ui.Input(param_name="username", placeholder="Yardi Voyager username"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Voyager Password", variant="caption"),
                    ui.Password(param_name="password", placeholder="Yardi Voyager password"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("ServerName", variant="caption"),
                    ui.Input(param_name="server_name", placeholder="e.g. yardiasp13.com"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Database", variant="caption"),
                    ui.Input(param_name="database", placeholder="Your Voyager database name"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Platform", variant="caption"),
                    ui.Input(param_name="platform", placeholder="Platform value from your Yardi rep"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("InterfaceEntity", variant="caption"),
                    ui.Input(param_name="interface_entity", placeholder="InterfaceEntity value for this license"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("InterfaceLicense", variant="caption"),
                    ui.Input(param_name="interface_license", placeholder="InterfaceLicense key for this interface"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Connection label (optional)", variant="caption"),
                    ui.Input(param_name="label", placeholder="e.g. Acme Portfolio -- Billing"),
                ]),
            ],
        ),
    ])


def _connections_summary(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Text("No Yardi interfaces connected yet.", variant="caption")
    by_interface: dict[str, int] = {}
    for c in connections:
        key = c.get("interface", "common_data")
        by_interface[key] = by_interface.get(key, 0) + 1
    lines = [
        f"{_INTERFACE_LABELS.get(k, k)}: {n} connection(s)"
        for k, n in by_interface.items()
    ]
    return ui.Stack(direction="v", gap=1, children=[
        ui.Text(t, variant="caption") for t in lines
    ])


@ext.panel("yardi_connect", slot="left", title="Yardi",
           default_width=340, min_width=280, max_width=440)
async def yardi_connect_panel(ctx, **kwargs) -> ui.UINode:
    connections = await _load_connections(ctx)

    header = ui.Header(text="Yardi", level=2,
                        subtitle="Manage your Yardi Voyager interface connections from Imperal")

    return ui.Stack(direction="v", gap=4, align="stretch", children=[
        header,
        _connections_summary(connections),
        ui.Divider(),
        ui.Button("View property audit", variant="primary", size="sm", icon="Building2", on_click=ui.Call("__panel__yardi_center")),
        ui.Divider(),
        _connect_form(),
        ui.Divider(),
        _settings_button(),
    ])


@ext.panel("yardi_center", slot="center", title="Yardi", icon="🏢", center_overlay=True)
async def yardi_center_panel(ctx, **kwargs) -> ui.UINode:
    """Base center panel -- per UI_INTERFACE_STANDARD.md (2026-08-20).
    This app has no list/detail content of its own to show in the center
    by default (everything lives in the sidebar). MUST carry
    center_overlay=True: per docs.imperal.io/en/concepts/panels, a plain
    slot="center" panel is registered but the Panel app never fetches it
    at session-init without that flag. Text is the shared canonical
    wording -- must stay identical across every app in this situation."""
    connections = await _load_connections(ctx)
    if not connections:
        return ui.Empty(message="Connect a Yardi interface from the sidebar to see it here.", icon="🏢")

    import handlers_audit as ha
    from schemas import AuditPropertiesParams
    common_data_conns = [c for c in connections if c.get("interface_type") == "common_data"] or connections
    conn_id = common_data_conns[0].get("id", "")
    result = await ha.audit_yardi_properties(ctx, AuditPropertiesParams(connection_id=conn_id))
    body: list[ui.UINode] = [ui.Text("Property audit", variant="subtitle")]
    if result.success and result.data:
        r = result.data
        body.append(ui.Stats(children=[
            ui.Stat(label="Properties", value=str(r.property_count)),
            ui.Stat(label="Findings", value=str(len(r.findings))),
        ]))
        for f in r.findings[:15]:
            color = {"high": "red", "medium": "yellow"}.get(f.severity, "gray")
            body.append(ui.Stack(direction="h", gap=2, align="center", children=[
                ui.Badge(label=(f.severity or "info").upper(), color=color),
                ui.Text(f.message, variant="body"),
            ]))
    else:
        body.append(ui.Text("Could not load the property audit.", variant="caption"))

    return ui.Stack(direction="v", gap=3, align="stretch", children=body)