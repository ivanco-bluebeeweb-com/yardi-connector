"""Extension declaration, secrets, lifecycle hooks.

WHY BYOK (bring-your-own-key), SAME REASONING AS EVERY OTHER CONNECTOR IN
THIS PORTFOLIO (Ironclad/Iguana/PagerDuty/MuleSoft/etc).

Yardi Voyager is the user's OWN property-management system instance --
Imperal cannot and should not broker access to someone else's leasing,
billing, and maintenance data centrally. The user supplies their own
per-interface WSDL URL plus the Login-block credentials Yardi itself
requires, Vault-encrypted via `ctx.secrets`, and every call runs against
their own Voyager instance.

WHY ONE CONNECTION = ONE INTERFACE, NOT ONE CONNECTION FOR THE WHOLE
VOYAGER ACCOUNT.

Confirmed by CONNECTOR_DISCOVERY.md SS1-2: Yardi's 7 "Standard Interfaces"
(Common Data, Billing & Payments, Vendor Invoicing, Service Requests,
Revenue Management, Lease Renewals, ILS/Guest Card) are separately
licensed, separately hosted (.asmx) SOAP services -- a client may only
have purchased some of them, and each has its own InterfaceLicense key.
Modeling this as N connections (one per interface a user has licensed),
each tagged with its `interface` field, mirrors reality far better than
pretending there is one unified "Yardi account" -- and lets a user
connect e.g. only Common Data + Billing without needing licenses they
don't have.

WHY `write_mode="both"`, SAME REASONING AS EVERY OTHER BYOK CONNECTOR.

Declaring `write_mode="user"` would mean only the platform's generic
Secrets screen could write these -- leaving a first-time user with no
in-app screen explaining what a Yardi WSDL URL or InterfaceLicense even
is. `"both"` keeps the generic Secrets screen as a fallback while letting
`connect_yardi` be the friendly guided path.

WHY SCOPE IS PER-ACCOUNT, NOT APP-LEVEL, SAME AS EVERY OTHER BYOK
CONNECTOR.

Each user connects their OWN Yardi Voyager interfaces -- these are not
developer-owned app credentials, so the connections secret is declared
per-account (default scope), not `scope="app"`.

WHY CONNECTIONS ARE STORED AS A JSON ARRAY UNDER ONE SECRET NAME, NOT ONE
SECRET PER CONNECTION.

Same "one secret holding a JSON array" precedent as every other multi-
connection BYOK connector in this portfolio (Ironclad/MuleSoft/PagerDuty/
Mirth Connect/Iguana).
"""
from __future__ import annotations

from imperal_sdk import Extension, ChatExtension

ext = Extension(
    "yardi-connector",
    version="1.0.0",
    display_name="Yardi",
    description=(
        "Connect your own Yardi Voyager Standard Interfaces (Common Data, "
        "Billing & Payments, Vendor Invoicing, Service Requests, Revenue "
        "Management, Lease Renewals, ILS/Guest Card) -- read and write "
        "properties, units, residents, leases, charges, payments, vendors, "
        "payables, purchase orders, budgets, maintenance work orders, lease "
        "renewals, and prospect/guest card data across your property "
        "management portfolio."
    ),
    icon="icon.svg",
    actions_explicit=True,
    capabilities=["yardi-connector:read", "yardi-connector:write"],
)

chat = ChatExtension(
    ext,
    tool_name="yardi_connector",
    description="Yardi Voyager connector -- chat tool entrypoint.",
)

ext.secret(
    "yardi_connections",
    (
        "Saved Yardi Voyager interface connections -- stored as a JSON "
        "array, one entry per connected Standard Interface, each with its "
        "own WSDL URL and Login-block credentials (UserName, Password, "
        "ServerName, Database, Platform, InterfaceEntity, "
        "InterfaceLicense) and a label. Managed through connect_yardi / "
        "disconnect_yardi -- you should not need to edit this directly."
    ),
    required=False,
    write_mode="both",
    max_bytes=65536,
    rotation_hint_days=180,
)(lambda: None)


@ext.health_check
async def health_check(ctx) -> dict:
    """Federal health check -- reports whether at least one interface
    connection is saved, without attempting a live SOAP call (that would
    cost the user's connection a wasted round trip on every platform
    health sweep)."""
    raw = await ctx.secrets.get("yardi_connections")
    try:
        import json
        connections = json.loads(raw) if raw else []
    except Exception:
        connections = []
    return {
        "ok": True,
        "connected": len(connections) > 0,
        "connection_count": len(connections),
    }
