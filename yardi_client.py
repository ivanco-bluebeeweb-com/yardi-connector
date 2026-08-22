"""Yardi Voyager SOAP client -- dynamic WSDL introspection + hand-built
SOAP 1.1 envelopes over `ctx.http` (stdlib xml.etree only, no zeep/lxml,
per the portfolio's "no dependency beyond imperal-sdk" convention -- see
requirements.txt).

WHY BYOK, SAME REASONING AS EVERY OTHER CONNECTOR IN THIS PORTFOLIO.

Yardi Voyager is the user's OWN property-management system instance --
Imperal cannot and should not broker access to someone else's leasing/
billing data centrally. The user supplies their own per-interface WSDL
URL plus the Login-block credentials (UserName/Password/ServerName/
Database/Platform/InterfaceEntity/InterfaceLicense) that Yardi itself
requires inside every SOAP call.

WHY DYNAMIC WSDL INTROSPECTION, NOT A HARDCODED NAMESPACE/SOAPACTION.

Yardi publishes no public specification for these interfaces (confirmed
CONNECTOR_DISCOVERY.md SS1) -- there is no single documented targetNamespace
or SOAPAction that is guaranteed to match every client's own Voyager
deployment. Hardcoding a namespace "seen in one example" would be
contract fabrication that could silently break on a different client's
install. Instead, on every operation call this client fetches
`<wsdl_url>?WSDL`, parses `wsdl:definitions/@targetNamespace` and finds
the matching `wsdl:binding/wsdl:operation[@name=...]/soap:operation/
@soapAction` -- the same thing a generated SOAP stub (zeep, in the
unofficial yardi-sdk reference) does, just without adding that
dependency. No `ctx.cache` is used for this (see CONNECTOR_DISCOVERY.md
SS2 for why: this is the first-ever use of that surface in the portfolio,
its TTL cap is only 300s, and this service has no live end-to-end test
yet -- an extra GET per call is a safer trade than an unproven cache
path on an unproven service).

WHY THE LOGIN-BLOCK PARAMETERS RIDE INSIDE THE XML BODY, NOT HTTP HEADERS.

Confirmed by reading yardi-sdk's endpoints/*.py (2026-08-22): every
generated endpoint class carries UserName/Password/ServerName/Database/
Platform/InterfaceEntity/InterfaceLicense as plain instance fields
alongside the operation's own business parameters -- this is Yardi's own
SOAP authentication model (a "Login block"), not a transport-level
Basic/Bearer scheme. This client therefore always merges the stored
connection's Login-block fields into every operation call's parameter
dict before building the envelope.

WHY A SINGLE GENERIC `call_operation`, NOT 150+ HAND-WRITTEN ENVELOPE
BUILDERS.

The operation surface is ~150 SOAP operations across 7 interfaces (see
CONNECTOR_DISCOVERY.md SS3-5). Each curated handler in handlers_*.py is a
thin, typed wrapper that calls `call_operation(...)` with the exact
parameter names Yardi expects (taken verbatim from yardi-sdk) -- the XML
envelope construction and response parsing logic lives in exactly one
place.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from typing import Any

_WSDL_NS = "http://schemas.xmlsoap.org/wsdl/"
_SOAP_BINDING_NS = "http://schemas.xmlsoap.org/wsdl/soap/"
_SOAP_ENVELOPE_NS = "http://schemas.xmlsoap.org/soap/envelope/"
_XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
_XSD_NS = "http://www.w3.org/2001/XMLSchema"

CONNECTION_INVALID = "CONNECTION_INVALID"
WSDL_UNREACHABLE = "WSDL_UNREACHABLE"
OPERATION_NOT_FOUND = "OPERATION_NOT_FOUND"
AUTH_REJECTED = "AUTH_REJECTED"
SOAP_FAULT = "SOAP_FAULT"
BACKEND_5XX = "BACKEND_5XX"
RESPONSE_UNEXPECTED = "RESPONSE_UNEXPECTED"
VALIDATION_FAILED = "VALIDATION_FAILED"

# Login-block field names Yardi expects on every *_Login-style operation,
# per yardi-sdk's endpoints/*.py -- these are merged into every call.
_LOGIN_FIELDS = (
    "UserName", "Password", "ServerName", "Database", "Platform",
    "InterfaceEntity", "InterfaceLicense",
)


class ClientFail(Exception):
    def __init__(self, payload: dict):
        self.payload = payload
        super().__init__(payload.get("error", "yardi client error"))


def fail(code: str, action: str, detail: str = "") -> dict:
    msg = {
        CONNECTION_INVALID: f"This Yardi connection is missing required fields to {action}.",
        WSDL_UNREACHABLE: f"Could not reach or parse the WSDL for this interface while trying to {action}.{(' ' + detail) if detail else ''}",
        OPERATION_NOT_FOUND: f"Operation not found in this interface's WSDL: {action}.{(' ' + detail) if detail else ''}",
        AUTH_REJECTED: f"Yardi rejected the Login-block credentials (UserName/Password/ServerName/Database/Platform/InterfaceEntity/InterfaceLicense) while trying to {action}.",
        SOAP_FAULT: f"Yardi returned a SOAP fault while trying to {action}.{(' ' + detail) if detail else ''}",
        BACKEND_5XX: f"Yardi's server returned an error while trying to {action}.",
        RESPONSE_UNEXPECTED: f"Unexpected response from Yardi while trying to {action}.{(' ' + detail) if detail else ''}",
        VALIDATION_FAILED: f"Yardi rejected the request while trying to {action}.{(' ' + detail) if detail else ''}",
    }.get(code, f"Error while trying to {action}.")
    return {"ok": False, "error": msg, "error_code": code}


def _local(tag: str) -> str:
    """Strip an XML namespace prefix, e.g. '{ns}Foo' -> 'Foo'."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


async def _fetch_wsdl(ctx, wsdl_url: str) -> str:
    url = wsdl_url if "?" in wsdl_url else f"{wsdl_url}?WSDL"
    resp = await ctx.http.get(url)
    if resp.status_code >= 500:
        raise ClientFail(fail(BACKEND_5XX, "fetch WSDL"))
    if resp.status_code != 200:
        raise ClientFail(fail(WSDL_UNREACHABLE, "fetch WSDL", f"HTTP {resp.status_code}"))
    body = resp.body if isinstance(resp.body, str) else str(resp.body or "")
    if not body.strip():
        raise ClientFail(fail(WSDL_UNREACHABLE, "fetch WSDL", "empty response body"))
    return body


def _resolve_operation(wsdl_xml: str, operation: str) -> dict:
    """Parse a WSDL document and return {target_namespace, soap_action,
    endpoint_url} for the named operation. Raises ClientFail if the WSDL
    can't be parsed or the operation isn't found in any binding."""
    try:
        root = ET.fromstring(wsdl_xml)
    except ET.ParseError as e:
        raise ClientFail(fail(WSDL_UNREACHABLE, "parse WSDL", str(e)))

    target_ns = root.attrib.get("targetNamespace", "")
    soap_action = ""
    for binding in root.iter(f"{{{_WSDL_NS}}}binding"):
        for op in binding.iter(f"{{{_WSDL_NS}}}operation"):
            if op.attrib.get("name") == operation:
                soap_op = op.find(f"{{{_SOAP_BINDING_NS}}}operation")
                if soap_op is not None:
                    soap_action = soap_op.attrib.get("soapAction", "")
                break

    endpoint_url = ""
    for service in root.iter(f"{{{_WSDL_NS}}}service"):
        for port in service.iter(f"{{{_WSDL_NS}}}port"):
            addr = port.find(f"{{{_SOAP_BINDING_NS}}}address")
            if addr is not None and addr.attrib.get("location"):
                endpoint_url = addr.attrib["location"]
                break
        if endpoint_url:
            break

    if not target_ns or not endpoint_url:
        raise ClientFail(fail(WSDL_UNREACHABLE, "resolve service endpoint from WSDL"))
    if not soap_action:
        raise ClientFail(fail(OPERATION_NOT_FOUND, "resolve operation", operation))

    return {"target_namespace": target_ns, "soap_action": soap_action, "endpoint_url": endpoint_url}


def _value_to_xml(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return escape(str(value))


def _build_envelope(operation: str, target_ns: str, params: dict) -> str:
    fields = "".join(
        f"<{k} xmlns=\"\">{_value_to_xml(v)}</{k}>" if v is not None else f"<{k} xmlns=\"\" xsi:nil=\"true\"/>"
        for k, v in params.items()
    )
    return (
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
        f"<soap:Envelope xmlns:xsi=\"{_XSI_NS}\" xmlns:xsd=\"{_XSD_NS}\" xmlns:soap=\"{_SOAP_ENVELOPE_NS}\">"
        "<soap:Body>"
        f"<{operation} xmlns=\"{target_ns}\">{fields}</{operation}>"
        "</soap:Body></soap:Envelope>"
    )


def _elem_to_value(elem: ET.Element):
    children = list(elem)
    if not children:
        return elem.text.strip() if elem.text else ""
    out: dict[str, Any] = {}
    for child in children:
        name = _local(child.tag)
        value = _elem_to_value(child)
        if name in out:
            if not isinstance(out[name], list):
                out[name] = [out[name]]
            out[name].append(value)
        else:
            out[name] = value
    return out


def _parse_response(raw_xml: str, operation: str, action: str) -> Any:
    try:
        root = ET.fromstring(raw_xml)
    except ET.ParseError as e:
        raise ClientFail(fail(RESPONSE_UNEXPECTED, action, f"could not parse XML response: {e}"))

    fault = None
    for el in root.iter():
        if _local(el.tag) == "Fault":
            fault = el
            break
    if fault is not None:
        detail = ""
        for el in fault.iter():
            tag = _local(el.tag)
            if tag in ("faultstring", "Reason", "Text") and el.text:
                detail = el.text.strip()
                break
        raise ClientFail(fail(SOAP_FAULT, action, detail))

    result_elem = None
    for el in root.iter():
        if _local(el.tag) == f"{operation}Result":
            result_elem = el
            break
    if result_elem is None:
        for el in root.iter():
            if _local(el.tag) == "Body":
                body_children = list(el)
                if body_children:
                    resp_wrapper = body_children[0]
                    inner = list(resp_wrapper)
                    result_elem = inner[0] if inner else resp_wrapper
                break

    if result_elem is None:
        return {}
    return _elem_to_value(result_elem)


def validate_connection(conn: dict) -> dict | None:
    """Returns a fail() dict if the connection is missing required
    Login-block fields, else None."""
    missing = [f for f in ("wsdl_url", "UserName", "Password", "ServerName", "Database", "InterfaceEntity", "InterfaceLicense") if not conn.get(f)]
    if missing:
        return fail(CONNECTION_INVALID, f"missing: {', '.join(missing)}")
    return None


async def call_operation(ctx, conn: dict, operation: str, params: dict | None = None) -> Any:
    """Call any Yardi SOAP operation on this connection's interface.

    `params` are the operation's OWN business parameters (e.g.
    YardiPropertyId, FromDate) -- the Login-block fields are merged in
    automatically from `conn`. Returns the parsed <Operation>Result
    subtree as a dict/str, or raises ClientFail.
    """
    invalid = validate_connection(conn)
    if invalid:
        raise ClientFail(invalid)

    wsdl_xml = await _fetch_wsdl(ctx, conn["wsdl_url"])
    resolved = _resolve_operation(wsdl_xml, operation)

    full_params = dict(params or {})
    for field in _LOGIN_FIELDS:
        if field not in full_params:
            full_params[field] = conn.get(field, "")

    envelope = _build_envelope(operation, resolved["target_namespace"], full_params)

    resp = await ctx.http.post(
        resolved["endpoint_url"],
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"{resolved["soap_action"]}"',
        },
        data=envelope,
    )
    raw_body = resp.body if isinstance(resp.body, str) else str(resp.body or "")

    if resp.status_code == 401 or resp.status_code == 403:
        raise ClientFail(fail(AUTH_REJECTED, operation))
    if resp.status_code >= 500:
        # Yardi (like many legacy ASMX services) returns 500 for SOAP
        # faults too -- inspect the body before assuming a backend error.
        if "<faultstring" in raw_body or "Fault" in raw_body:
            return _parse_response(raw_body, operation, operation)
        raise ClientFail(fail(BACKEND_5XX, operation))
    if resp.status_code not in (200, 500):
        raise ClientFail(fail(RESPONSE_UNEXPECTED, operation, f"HTTP {resp.status_code}"))

    return _parse_response(raw_body, operation, operation)


async def list_wsdl_operations(ctx, wsdl_url: str) -> tuple[str, list[tuple[str, str]]]:
    """Introspect a WSDL and return (target_namespace, [(operation_name,
    soap_action), ...]) for every operation declared across all its
    bindings. Used by list_yardi_wsdl_operations() so a user/agent can
    discover exactly which operations THEIR OWN Voyager deployment
    exposes -- licensed operation sets differ between clients (see
    module docstring)."""
    wsdl_xml = await _fetch_wsdl(ctx, wsdl_url)
    try:
        root = ET.fromstring(wsdl_xml)
    except ET.ParseError as e:
        raise ClientFail(fail(WSDL_UNREACHABLE, "parse WSDL", str(e)))

    target_ns = root.attrib.get("targetNamespace", "")
    seen: dict[str, str] = {}
    for binding in root.iter(f"{{{_WSDL_NS}}}binding"):
        for op in binding.iter(f"{{{_WSDL_NS}}}operation"):
            name = op.attrib.get("name", "")
            if not name or name in seen:
                continue
            soap_op = op.find(f"{{{_SOAP_BINDING_NS}}}operation")
            seen[name] = soap_op.attrib.get("soapAction", "") if soap_op is not None else ""
    return target_ns, sorted(seen.items())


async def check_connection(ctx, conn: dict) -> dict:
    """Verify a connection by calling the interface's own Ping (or
    GetVersionNumber as a fallback) operation -- both are documented as
    present on every Yardi Standard Interface (yardi-sdk endpoints/*.py)."""
    try:
        await call_operation(ctx, conn, "Ping", {})
        return {"ok": True}
    except ClientFail as e:
        if e.payload.get("error_code") == OPERATION_NOT_FOUND:
            try:
                await call_operation(ctx, conn, "GetVersionNumber", {})
                return {"ok": True}
            except ClientFail as e2:
                return e2.payload
        return e.payload
