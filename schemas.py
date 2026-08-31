"""Pydantic params models + SDL entity contracts for Yardi Connector.

All params models are module-scope (V17 federal invariant, same rule as
every other connector's schemas.py in this portfolio).
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from imperal_sdk import sdl


class NoParams(BaseModel):
    """Explicit empty params model -- V17 disallows untyped handlers."""
    pass


# ──────────────────────────────────────────────────────────────────────────
# Connection
# ──────────────────────────────────────────────────────────────────────────

INTERFACE_CHOICES = (
    "common_data", "billing_and_payments", "vendor_invoicing",
    "service_requests", "revenue_management", "lease_renewals",
    "ils_guest_card",
)


class ConnectYardiParams(BaseModel):
    wsdl_url: str = Field(
        "",
        description="Full WSDL URL for this interface, e.g. https://www.yardiasp13.com/yourclient/webservices/ItfCommonData.asmx?WSDL",
    )
    interface: str = Field(
        "common_data",
        description="Which Yardi Standard Interface this WSDL belongs to: common_data, billing_and_payments, vendor_invoicing, service_requests, revenue_management, lease_renewals, or ils_guest_card.",
    )
    username: str = Field("", description="Yardi Voyager UserName for this interface's Login block.")
    password: str = Field("", description="Yardi Voyager Password for this interface's Login block.")
    server_name: str = Field("", description="Yardi ServerName (from Voyager Administration > About > URL).")
    database: str = Field("", description="Yardi Database name for this Voyager instance.")
    platform: str = Field("", description="Yardi Platform value (as issued by your Yardi representative).")
    interface_entity: str = Field("", description="Yardi InterfaceEntity value for this interface license.")
    interface_license: str = Field("", description="Yardi InterfaceLicense key issued for this specific interface.")
    label: str = Field("", description="Optional friendly name for this interface connection, e.g. 'Acme Portfolio - Billing'.")


class ProviderConnection(sdl.Entity):
    id: str = ""
    title: str = ""
    connected: bool = False
    detail: str = ""
    interface: str = ""
    wsdl_url: str = ""


class ProviderConnectionList(sdl.Entity):
    id: str = ""
    title: str = ""
    connections: list[ProviderConnection] = []


class DisconnectYardiParams(BaseModel):
    connection_id: str = Field("", description="ID of the interface connection to disconnect.")


class DeleteResult(sdl.Entity):
    title: str = ""
    deleted: bool = False
    id: str = ""


class ConnectionRefParams(BaseModel):
    connection_id: str = Field("", description="ID of the Yardi interface connection to use. Omit to use the only/most recent one for that interface.")


# ──────────────────────────────────────────────────────────────────────────
# Universal passthrough (Tier 3 -- full coverage of every SOAP operation)
# ──────────────────────────────────────────────────────────────────────────


class CallYardiOperationParams(BaseModel):
    connection_id: str = Field("", description="ID of the Yardi interface connection to use. Omit to use the only/most recent one for that interface.")
    operation: str = Field(..., description="Exact SOAP operation name to call, e.g. GetResidents, ImportCharge_Login, GetPurchaseOrders.")
    parameters_json: str = Field(
        "{}",
        description='JSON object of the operation\'s own parameters (excluding the Login block, which is added automatically), e.g. {"YardiPropertyId": "123", "FromDate": "2026-01-01"}.',
    )


class YardiOperationResult(sdl.Entity):
    id: str = ""
    title: str = ""
    operation: str = ""
    raw_xml: str = ""
    parsed: dict = {}


class ListWsdlOperationsParams(BaseModel):
    connection_id: str = Field("", description="ID of the Yardi interface connection whose WSDL to introspect.")


class WsdlOperation(sdl.Entity):
    id: str = ""
    title: str = ""
    name: str = ""
    soap_action: str = ""


class WsdlOperationList(sdl.Entity):
    id: str = ""
    title: str = ""
    target_namespace: str = ""
    operations: list[WsdlOperation] = []


# ──────────────────────────────────────────────────────────────────────────
# Common Data interface -- properties, units, residents, leases, documents
# ──────────────────────────────────────────────────────────────────────────


class PropertyRefParams(BaseModel):
    connection_id: str = Field("", description="ID of the Common Data interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id, e.g. 'p1001'.")


class ListPropertiesParams(BaseModel):
    connection_id: str = Field("", description="ID of the Common Data interface connection to use.")


class DateRangeParams(BaseModel):
    connection_id: str = Field("", description="ID of the Common Data interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id, e.g. 'p1001'.")
    from_date: str = Field(..., description="Start date, YYYY-MM-DD.")
    to_date: str = Field("", description="End date, YYYY-MM-DD. Leave blank for open-ended ranges where supported.")


class ResidentRefParams(BaseModel):
    connection_id: str = Field("", description="ID of the Common Data interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id, e.g. 'p1001'.")
    tenant_code: str = Field("", description="Yardi tenant/resident code, if narrowing to one resident.")


class UnitInfoParams(BaseModel):
    connection_id: str = Field("", description="ID of the Common Data interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id, e.g. 'p1001'.")
    unit_id: str = Field("", description="Yardi unit id, if narrowing to one unit.")


class ImportContactsParams(BaseModel):
    connection_id: str = Field("", description="ID of the Common Data interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id the contact belongs to.")
    contacts_json: str = Field(..., description='JSON array of contact objects, matching the Common Data ImportContacts XML shape, e.g. [{"FirstName": "Jane", "LastName": "Doe", "Role": "Emergency"}].')


class RentrollParams(BaseModel):
    connection_id: str = Field("", description="ID of the Common Data interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id, e.g. 'p1001'.")


class LeaseInfoParams(BaseModel):
    connection_id: str = Field("", description="ID of the Common Data interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id, e.g. 'p1001'.")
    tenant_code: str = Field("", description="Yardi tenant/resident code, if narrowing to one lease.")


class YardiRecordList(sdl.Entity):
    id: str = ""
    title: str = ""
    interface: str = ""
    operation: str = ""
    records: list[dict] = []
    record_count: int = 0


class YardiRecord(sdl.Entity):
    id: str = ""
    title: str = ""
    interface: str = ""
    operation: str = ""
    record: dict = {}


# ──────────────────────────────────────────────────────────────────────────
# Billing & Payments interface -- transactions, charges, prepays, payables
# ──────────────────────────────────────────────────────────────────────────


class ResidentTransactionsParams(BaseModel):
    connection_id: str = Field("", description="ID of the Billing & Payments interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id, e.g. 'p1001'.")
    from_date: str = Field("", description="Start date, YYYY-MM-DD. Leave blank for all transactions.")
    to_date: str = Field("", description="End date, YYYY-MM-DD.")


class ImportChargeParams(BaseModel):
    connection_id: str = Field("", description="ID of the Billing & Payments interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id the charge is posted to.")
    tenant_code: str = Field(..., description="Yardi tenant/resident code the charge applies to.")
    charge_code: str = Field(..., description="Yardi charge code, e.g. 'LATE' or 'RENT'.")
    amount: float = Field(..., description="Charge amount, e.g. 150.00.")
    charge_date: str = Field(..., description="Date the charge is posted on, YYYY-MM-DD.")
    memo: str = Field("", description="Optional memo/description shown on the resident's ledger.")


class ImportReceiptParams(BaseModel):
    connection_id: str = Field("", description="ID of the Billing & Payments interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id the payment is received at.")
    tenant_code: str = Field(..., description="Yardi tenant/resident code making the payment.")
    amount: float = Field(..., description="Payment amount received, e.g. 1200.00.")
    receipt_date: str = Field(..., description="Date the payment was received, YYYY-MM-DD.")
    payment_type: str = Field("", description="Payment method/type, e.g. 'Check', 'ACH', 'CreditCard'.")


class ImportPayableParams(BaseModel):
    connection_id: str = Field("", description="ID of the Billing & Payments interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id the payable is against.")
    vendor_code: str = Field(..., description="Yardi vendor code being paid.")
    amount: float = Field(..., description="Payable amount, e.g. 4500.00.")
    invoice_date: str = Field(..., description="Vendor invoice date, YYYY-MM-DD.")
    invoice_number: str = Field("", description="Vendor's own invoice number, for reconciliation.")
    gl_account: str = Field("", description="GL account code to post the payable against.")
    memo: str = Field("", description="Optional memo describing the payable.")


class VendorRefParams(BaseModel):
    connection_id: str = Field("", description="ID of the interface connection to use.")
    vendor_code: str = Field("", description="Yardi vendor code, if looking up one vendor.")


# ──────────────────────────────────────────────────────────────────────────
# Vendor Invoicing interface -- invoice register, purchase orders, budgets
# ──────────────────────────────────────────────────────────────────────────


class InvoiceRegisterParams(BaseModel):
    connection_id: str = Field("", description="ID of the Vendor Invoicing interface connection to use.")
    yardi_property_id: str = Field("", description="Yardi property id to scope invoices to. Leave blank for all properties this license covers.")
    from_date: str = Field("", description="Start date, YYYY-MM-DD.")
    to_date: str = Field("", description="End date, YYYY-MM-DD.")


class ImportInvoiceRegisterParams(BaseModel):
    connection_id: str = Field("", description="ID of the Vendor Invoicing interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id the invoice is for.")
    vendor_code: str = Field(..., description="Yardi vendor code on the invoice.")
    invoice_number: str = Field(..., description="Vendor's own invoice number.")
    invoice_date: str = Field(..., description="Invoice date, YYYY-MM-DD.")
    amount: float = Field(..., description="Invoice total amount, e.g. 3200.00.")
    gl_account: str = Field("", description="GL account code to post the invoice against.")
    purchase_order_number: str = Field("", description="Related purchase order number, if any.")


class PurchaseOrderParams(BaseModel):
    connection_id: str = Field("", description="ID of the Vendor Invoicing interface connection to use.")
    yardi_property_id: str = Field("", description="Yardi property id to scope purchase orders to.")
    from_date: str = Field("", description="Only POs modified on/after this date, YYYY-MM-DD. Leave blank for all.")


class ImportPurchaseOrderParams(BaseModel):
    connection_id: str = Field("", description="ID of the Vendor Invoicing interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id the PO is for.")
    vendor_code: str = Field(..., description="Yardi vendor code the PO is issued to.")
    amount: float = Field(..., description="Total PO amount, e.g. 8000.00.")
    description: str = Field("", description="Short description of what the PO covers.")
    gl_account: str = Field("", description="GL account code the PO should post against.")


class JobCostParams(BaseModel):
    connection_id: str = Field("", description="ID of the Vendor Invoicing interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id to read job cost data for.")


class BudgetParams(BaseModel):
    connection_id: str = Field("", description="ID of the Vendor Invoicing interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id to read the budget for.")
    month: str = Field("", description="Specific budget month, YYYY-MM. Leave blank for the full-year budget.")


# ──────────────────────────────────────────────────────────────────────────
# Service Requests interface -- maintenance / work orders
# ──────────────────────────────────────────────────────────────────────────


class ServiceRequestSearchParams(BaseModel):
    connection_id: str = Field("", description="ID of the Service Requests interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id to search service requests within.")
    from_date: str = Field("", description="Start date, YYYY-MM-DD. Leave blank for all open requests.")
    to_date: str = Field("", description="End date, YYYY-MM-DD.")


class CreateServiceRequestParams(BaseModel):
    connection_id: str = Field("", description="ID of the Service Requests interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id the request is for.")
    unit_id: str = Field(..., description="Yardi unit id the maintenance request applies to.")
    tenant_code: str = Field("", description="Yardi tenant/resident code reporting the issue, if applicable.")
    problem_description: str = Field(..., description="Description of the maintenance issue, e.g. 'Leaking kitchen faucet'.")
    priority: str = Field("Normal", description="Request priority, e.g. 'Normal', 'Urgent', 'Emergency'.")
    category: str = Field("", description="Maintenance category/custom value code, if your Voyager setup requires one.")


class ServiceRequestAttachmentParams(BaseModel):
    connection_id: str = Field("", description="ID of the Service Requests interface connection to use.")
    service_request_id: str = Field(..., description="Yardi service request id to search attachments for.")


# ──────────────────────────────────────────────────────────────────────────
# Revenue Management interface
# ──────────────────────────────────────────────────────────────────────────


class RevenuePropertyParams(BaseModel):
    connection_id: str = Field("", description="ID of the Revenue Management interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id to read revenue management data for.")


class ImportRevenueParams(BaseModel):
    connection_id: str = Field("", description="ID of the Revenue Management interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id the revenue import applies to.")
    payload_json: str = Field(..., description='JSON object matching the Revenue Management ImportRM/ImportMR XML shape for this property (unit-level rent/pricing updates).')


# ──────────────────────────────────────────────────────────────────────────
# Lease Renewals interface
# ──────────────────────────────────────────────────────────────────────────


class ScheduledRenewalsParams(BaseModel):
    connection_id: str = Field("", description="ID of the Lease Renewals interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id to read scheduled lease renewals for.")


class LeaseOffersParams(BaseModel):
    connection_id: str = Field("", description="ID of the Lease Renewals interface connection to use.")
    yardi_property_id: str = Field("", description="Yardi property id to scope lease offers to. Leave blank for all properties this license covers.")


class ImportRenewalSelectionParams(BaseModel):
    connection_id: str = Field("", description="ID of the Lease Renewals interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id the renewal applies to.")
    tenant_code: str = Field(..., description="Yardi tenant/resident code renewing their lease.")
    selected_offer_id: str = Field(..., description="The lease offer id (from list_lease_offers) the resident selected.")
    new_lease_start: str = Field("", description="New lease start date, YYYY-MM-DD, if different from the offer default.")
    new_lease_end: str = Field("", description="New lease end date, YYYY-MM-DD, if different from the offer default.")


# ──────────────────────────────────────────────────────────────────────────
# ILS / Guest Card interface -- leasing/prospect pipeline
# ──────────────────────────────────────────────────────────────────────────


class AvailableUnitsParams(BaseModel):
    connection_id: str = Field("", description="ID of the ILS/Guest Card interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id to check unit availability for.")


class ImportGuestCardParams(BaseModel):
    connection_id: str = Field("", description="ID of the ILS/Guest Card interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id the prospect is interested in.")
    first_name: str = Field(..., description="Prospect's first name.")
    last_name: str = Field(..., description="Prospect's last name.")
    email: str = Field("", description="Prospect's email address.")
    phone: str = Field("", description="Prospect's phone number.")
    source: str = Field("", description="Lead source name, e.g. 'Zillow', 'Apartments.com', 'Walk-in'.")
    desired_move_in: str = Field("", description="Prospect's desired move-in date, YYYY-MM-DD.")
    notes: str = Field("", description="Any free-text notes about the prospect's visit/interest.")


class GuestActivitySearchParams(BaseModel):
    connection_id: str = Field("", description="ID of the ILS/Guest Card interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id to search prospect/guest activity for.")
    from_date: str = Field("", description="Start date, YYYY-MM-DD. Leave blank for all activity.")
    to_date: str = Field("", description="End date, YYYY-MM-DD.")


class ApplicationParams(BaseModel):
    connection_id: str = Field("", description="ID of the ILS/Guest Card interface connection to use.")
    application_id: str = Field(..., description="Yardi application id to read.")


class ImportApplicationParams(BaseModel):
    connection_id: str = Field("", description="ID of the ILS/Guest Card interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id the application is for.")
    unit_id: str = Field(..., description="Yardi unit id being applied for.")
    first_name: str = Field(..., description="Applicant's first name.")
    last_name: str = Field(..., description="Applicant's last name.")
    email: str = Field("", description="Applicant's email address.")
    desired_move_in: str = Field("", description="Applicant's desired move-in date, YYYY-MM-DD.")


# ──────────────────────────────────────────────────────────────────────────
# Value-add: audit / cross-interface reports (Imperal-side, not Yardi's)
# ──────────────────────────────────────────────────────────────────────────


class AuditPropertiesParams(BaseModel):
    connection_id: str = Field("", description="ID of the Common Data interface connection to audit.")


class AuditFinding(sdl.Entity):
    id: str = ""
    title: str = ""
    severity: str = ""
    yardi_property_id: str = ""
    message: str = ""


class AuditReport(sdl.Entity):
    id: str = ""
    title: str = ""
    checked_at: str = ""
    property_count: int = 0
    findings: list[AuditFinding] = []


class DelinquencyReportParams(BaseModel):
    connection_id: str = Field("", description="ID of the Billing & Payments interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id to build the delinquency report for.")
    as_of_date: str = Field("", description="Report as-of date, YYYY-MM-DD. Leave blank for today.")


class DelinquentResident(sdl.Entity):
    id: str = ""
    title: str = ""
    tenant_code: str = ""
    resident_name: str = ""
    balance_due: float = 0.0
    days_late: int = 0


class DelinquencyReport(sdl.Entity):
    id: str = ""
    title: str = ""
    yardi_property_id: str = ""
    as_of_date: str = ""
    total_balance_due: float = 0.0
    residents: list[DelinquentResident] = []


class OpenWorkOrdersReportParams(BaseModel):
    connection_id: str = Field("", description="ID of the Service Requests interface connection to use.")
    yardi_property_id: str = Field(..., description="Yardi property id to build the open work orders report for.")


class OpenWorkOrder(sdl.Entity):
    id: str = ""
    title: str = ""
    service_request_id: str = ""
    unit_id: str = ""
    priority: str = ""
    days_open: int = 0
    description: str = ""


class OpenWorkOrdersReport(sdl.Entity):
    id: str = ""
    title: str = ""
    yardi_property_id: str = ""
    open_count: int = 0
    urgent_count: int = 0
    work_orders: list[OpenWorkOrder] = []
