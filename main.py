"""Entrypoint for the web-kernel and CLI tools (imperal validate/build).

Sets up sys.path, purges stale module cache, then imports ext/chat and all
handler modules so their decorators register on the same Extension instance
-- same pattern as Ironclad/Iguana/PagerDuty Connector's main.py.
"""

import os
import sys

_EXT_DIR = os.path.dirname(os.path.abspath(__file__))
if _EXT_DIR not in sys.path:
    sys.path.insert(0, _EXT_DIR)

_LOCAL = (
    "app", "schemas", "yardi_client",
    "handlers_connection", "handlers_common_data", "handlers_billing",
    "handlers_vendor_invoicing", "handlers_service_requests",
    "handlers_revenue", "handlers_lease_renewals", "handlers_ils_guest_card",
    "handlers_passthrough", "handlers_audit",
    "panels", "panels_settings",
)
for _mod in _LOCAL:
    sys.modules.pop(_mod, None)

from app import ext, chat  # noqa: E402,F401
import handlers_connection  # noqa: E402,F401
import handlers_common_data  # noqa: E402,F401
import handlers_billing  # noqa: E402,F401
import handlers_vendor_invoicing  # noqa: E402,F401
import handlers_service_requests  # noqa: E402,F401
import handlers_revenue  # noqa: E402,F401
import handlers_lease_renewals  # noqa: E402,F401
import handlers_ils_guest_card  # noqa: E402,F401
import handlers_passthrough  # noqa: E402,F401
import handlers_audit  # noqa: E402,F401
import panels  # noqa: E402,F401
import panels_settings  # noqa: E402,F401
