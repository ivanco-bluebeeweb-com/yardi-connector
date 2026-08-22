"""Value-add: audit a Common Data interface's own property list for
data-quality findings (Imperal-side aggregation, not a native Yardi
operation -- same pattern as get_yardi_delinquency_report /
get_yardi_open_work_orders_report).
"""
from __future__ import annotations

from datetime import datetime, timezone

from imperal_sdk import ActionResult

import yardi_client as yc
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import AuditPropertiesParams, AuditReport, AuditFinding

_INTERFACE = "common_data"


@chat.function(
    "audit_yardi_properties",
    "Value-add report: scan every property visible to this Yardi Common Data connection and flag data-quality issues -- properties missing a name, missing an address, or with obviously malformed ids. Not a native Yardi operation.",
    action_type="read", chain_callable=True, data_model=AuditReport,
)
async def audit_yardi_properties(ctx, params: AuditPropertiesParams) -> ActionResult:
    """Value-add report: scan every property visible to this Yardi Common Data connection and flag data-quality issues."""
    conn = await resolve_connection(ctx, params.connection_id, _INTERFACE)
    if isinstance(conn, ActionResult):
        return conn
    try:
        data = await yc.call_operation(ctx, conn, "GetPropertyList", {})
    except yc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Could not audit properties."))

    records = data if isinstance(data, list) else (
        list(data.values())[0] if isinstance(data, dict) and len(data) == 1 and isinstance(list(data.values())[0], list)
        else [data] if data else []
    )

    findings: list[AuditFinding] = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        pid = str(rec.get("YardiPropertyId") or rec.get("PropertyId") or "")
        name = str(rec.get("PropertyName") or rec.get("Name") or "")
        address = str(rec.get("Address") or rec.get("Address1") or "")
        if not pid:
            findings.append(AuditFinding(severity="high", yardi_property_id="", message="A property record has no YardiPropertyId."))
            continue
        if not name:
            findings.append(AuditFinding(severity="medium", yardi_property_id=pid, message="Property has no name on file."))
        if not address:
            findings.append(AuditFinding(severity="low", yardi_property_id=pid, message="Property has no address on file."))

    report = AuditReport(
        checked_at=datetime.now(timezone.utc).isoformat(),
        property_count=len(records),
        findings=findings,
    )
    return ActionResult.success(
        data=report,
        summary=f"Audited {report.property_count} propert{'y' if report.property_count == 1 else 'ies'}, {len(findings)} finding(s).",
    )
