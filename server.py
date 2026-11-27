#!/usr/bin/env python3

import base64
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import quote

import requests
from fastmcp import FastMCP, Context
from mcp.types import ToolAnnotations

__version__ = "0.1.0"  # = pyproject.toml and server.json (tests/test_packaging.py)

mcp = FastMCP(name="superfaktura", version=__version__)

# Tools that change data in SuperFaktura. SUPERFAKTURA_READ_ONLY=1 leaves them out.
WRITE_TOOLS = {
    "create_invoice", "edit_invoice", "delete_invoice", "send_invoice", "mark_invoice_paid",
    "set_invoice_language", "create_client", "update_client", "delete_client",
    "create_expense", "edit_expense", "delete_expense",
}
DESTRUCTIVE_TOOLS = {"delete_invoice", "delete_client", "delete_expense", "send_invoice"}


def _ann(name: str) -> ToolAnnotations:
    """MCP hints so clients can ask before a write and warn before a destructive call."""
    if name not in WRITE_TOOLS:
        return ToolAnnotations(readOnlyHint=True, openWorldHint=True)
    return ToolAnnotations(readOnlyHint=False, destructiveHint=name in DESTRUCTIVE_TOOLS, openWorldHint=True)


# Language list, docs value-lists.md (ISO 639-2)
LANGUAGES = {"cze", "deu", "eng", "hrv", "hun", "ita", "nld", "pol", "rom", "rus", "slo", "slv", "spa", "ukr"}


def _language(code: Optional[str]) -> Optional[str]:
    """Normalized language code, or None when it is not one SuperFaktura knows."""
    code = (code or "").strip().lower()
    return code if code in LANGUAGES else None


def _bad_language(code: str) -> Dict[str, Any]:
    return {"error": f"Unknown language {code!r}. Use one of: {', '.join(sorted(LANGUAGES))}.", "status": "failed"}


def _seg(key: str, value: Any) -> str:
    """One `key:value` URL segment. The value is percent-encoded, so text from the model can
    never add a path segment, a query or a fragment ('|' and ',' stay: multi-value and base64)."""
    return f"{key}:{quote(str(value), safe='|,')}"


def _sf_b64(text: str) -> str:
    """Base64 the way the SuperFaktura docs want it in URLs (intro.md): + -> -, / -> _, = -> ,"""
    raw = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return raw.replace("+", "-").replace("/", "_").replace("=", ",")


BASE_URLS = {
    "sk": "https://moja.superfaktura.sk",
    "cz": "https://moje.superfaktura.cz",
    "at": "https://meine.superfaktura.at",
    "sandbox-sk": "https://sandbox.superfaktura.sk",
    "sandbox-cz": "https://sandbox.superfaktura.cz",
}


class SuperFakturaClient:
    """
    Client for interacting with SuperFaktura API.

    Supports both environment variables (for single-tenant/local development)
    or explicit arguments.
    """

    def __init__(
        self,
        email: Optional[str] = None,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        country: Optional[str] = None,
        company_id: Optional[str] = None,
        module: str = "superfaktura-mcp/0.1.0",
    ):
        """
        Initialize SuperFaktura API client.

        Args:
            email: Account email (falls back to SUPERFAKTURA_EMAIL env var)
            api_key: API key (falls back to SUPERFAKTURA_API_KEY env var)
            api_url: Custom API URL (falls back to SUPERFAKTURA_API_URL env var)
            country: Country code - sk, cz, at, sandbox-sk, sandbox-cz (default: sk)
            company_id: Company ID (optional, falls back to SUPERFAKTURA_COMPANY_ID env var)
            module: Module identifier for API (default: superfaktura-mcp/0.1.0)

        Raises:
            ValueError: If credentials are not provided via parameters or environment variables
        """
        self.email = email or os.getenv("SUPERFAKTURA_EMAIL")
        self.api_key = api_key or os.getenv("SUPERFAKTURA_API_KEY")
        self.company_id = company_id or os.getenv("SUPERFAKTURA_COMPANY_ID")
        self.module = module

        if not self.email or not self.api_key:
            raise ValueError(
                "SuperFaktura credentials required. "
                "Provide email and api_key parameters, or set "
                "SUPERFAKTURA_EMAIL and SUPERFAKTURA_API_KEY environment variables."
            )

        # Support custom API URL or use country-based URL
        self.base_url = api_url or os.getenv("SUPERFAKTURA_API_URL")
        if not self.base_url:
            resolved_country = (country or os.getenv("SUPERFAKTURA_COUNTRY") or "sk").strip().lower()
            self.base_url = BASE_URLS.get(resolved_country)
            if not self.base_url:
                raise ValueError(f"Invalid country code: {resolved_country}")

    def _get_headers(self) -> Dict[str, str]:
        """Generate authentication headers per SuperFaktura API spec."""
        from urllib.parse import quote

        auth_parts = [
            f"email={quote(self.email)}",
            f"apikey={quote(self.api_key)}",
            f"module={quote(self.module)}",
        ]

        if self.company_id:
            auth_parts.append(f"company_id={quote(self.company_id)}")

        return {
            "Authorization": f"SFAPI {'&'.join(auth_parts)}",
            "Content-Type": "application/json",
        }

    RETRIES_429 = 2  # ponytail: short fixed backoff; a daily/monthly limit will not clear by waiting

    def _send(self, method: str, endpoint: str, data: Optional[Dict] = None, timeout: int = 30):
        """One request with a short backoff on HTTP 429. Returns (response, None) or (None, error dict)."""
        url = f"{self.base_url}/{endpoint}"
        for attempt in range(self.RETRIES_429 + 1):
            try:
                response = requests.request(
                    method=method, url=url, json=data, headers=self._get_headers(), timeout=timeout
                )
            except requests.exceptions.RequestException as e:
                return None, {"error": str(e), "status": "failed"}
            if response.status_code == 429 and attempt < self.RETRIES_429:
                time.sleep(2 ** attempt)
                continue
            if response.status_code >= 400:
                err: Dict[str, Any] = {
                    "error": f"SuperFaktura returned HTTP {response.status_code}",
                    "status": "failed",
                    "http_status": response.status_code,
                    "body": (getattr(response, "text", "") or "")[:500],
                }
                message = (getattr(response, "headers", None) or {}).get("X-RateLimit-Message")
                if message:
                    err["rate_limit_message"] = message
                return None, err
            return response, None
        return None, {"error": "unreachable", "status": "failed"}

    def _request(
        self, method: str, endpoint: str, data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to SuperFaktura API."""
        response, err = self._send(method, endpoint, data)
        if err:
            return err
        try:
            return response.json()
        except ValueError as e:
            return {"error": f"SuperFaktura did not return JSON: {e}", "status": "failed"}

    def get_bytes(self, endpoint: str):
        """GET a binary file (PDF). Returns (bytes, None) or (None, error dict)."""
        response, err = self._send("GET", endpoint, timeout=60)
        return (None, err) if err else (response.content, None)

    def get(self, endpoint: str) -> Dict[str, Any]:
        """GET request."""
        return self._request("GET", endpoint)

    def post(self, endpoint: str, data: Dict) -> Dict[str, Any]:
        """POST request."""
        return self._request("POST", endpoint, data)

    def patch(self, endpoint: str, data: Dict) -> Dict[str, Any]:
        """PATCH request."""
        return self._request("PATCH", endpoint, data)

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE request."""
        return self._request("DELETE", endpoint)


def _view_invoice(sf: SuperFakturaClient, invoice_id: int):
    """GET invoices/view. Returns (Invoice dict, None) or (None, error dict).

    Success is explicit, per invoice.md "Get invoice detail": the body carries an "Invoice"
    object with an id and has no `error` key. "Wrong invoice" is {"error": 1, "error_message": ...}.
    A missing `error` key alone never counts as success."""
    body = sf.get(f"invoices/view/{invoice_id}.json")
    if not isinstance(body, dict) or body.get("status") == "failed":
        return None, body if isinstance(body, dict) else {"error": "Unexpected response.", "status": "failed"}
    invoice = body.get("Invoice")
    if body.get("error") in (None, 0, "0") and isinstance(invoice, dict) and invoice.get("id"):
        return invoice, None
    message = body.get("error_message") or body.get("message") or "no Invoice in the response"
    return None, {"error": f"Invoice {invoice_id} not found: {message}", "status": "failed", "response": body}


def _get_nested_value(data: Any, path: str) -> Any:
    """
    Get value from nested dictionary using dot notation.

    Args:
        data: Data to extract from (dict, list, or primitive)
        path: Dot-separated path (e.g., "Invoice.id" or "items.0.Client.name")

    Returns:
        Extracted value or None if path doesn't exist
    """
    if not path:
        return data

    parts = path.split(".", 1)
    key = parts[0]
    remaining = parts[1] if len(parts) > 1 else ""

    # Handle list indexing (e.g., "items" when data is a list)
    if isinstance(data, list):
        # If key is a number, treat as index
        if key.isdigit():
            idx = int(key)
            if 0 <= idx < len(data):
                return _get_nested_value(data[idx], remaining)
            return None
        # Otherwise, apply to all items in the list
        results = []
        for item in data:
            val = _get_nested_value(item, path)
            if val is not None:
                results.append(val)
        return results if results else None

    # Handle dictionary access
    if isinstance(data, dict):
        if key not in data:
            return None
        return _get_nested_value(data[key], remaining)

    # Can't traverse further
    return None


def _apply_fields_filter(data: Dict[str, Any], fields_filter: Optional[List[str]]) -> Any:
    """
    Filter API response to return only specified fields as array of arrays (rows).

    Args:
        data: API response data to filter
        fields_filter: List of dot-separated field paths to extract
                      - None (not passed): return all data unchanged
                      - [] (empty array): return empty array
                      - ["field1", "field2"]: return filtered fields as array of arrays

    Returns:
        - Original data if fields_filter is None
        - Empty array if fields_filter is []
        - Array of arrays where each inner array contains values for requested attributes (one row per record)

    Examples:
        None -> {original response data}
        [] -> []
        ["items.Invoice.id", "items.Invoice.name"] -> [[1, "Invoice A"], [2, "Invoice B"], ...]
        ["Invoice.id", "Invoice.name"] -> [[123, "My Invoice"]]
        ["itemCount"] -> [[42]]
    """
    if fields_filter is None:
        return data

    if not fields_filter:  # empty list
        return []

    # Extract all values for each field path
    extracted_values = []
    for field_path in fields_filter:
        value = _get_nested_value(data, field_path)
        extracted_values.append(value)

    # Check if all values are lists (meaning we're extracting from array data)
    all_lists = all(isinstance(v, list) for v in extracted_values if v is not None)

    if all_lists and extracted_values:
        # Get all non-None list values
        list_values = [v for v in extracted_values if v is not None and isinstance(v, list)]

        if not list_values:
            return []

        # Find the maximum length (in case lists have different lengths)
        max_len = max(len(v) for v in list_values)

        # Zip values together into rows
        # Use None for missing values if lists have different lengths
        rows = []
        for i in range(max_len):
            row = []
            for value in extracted_values:
                if value is None:
                    row.append(None)
                elif isinstance(value, list):
                    row.append(value[i] if i < len(value) else None)
                else:
                    # Scalar value - repeat for each row
                    row.append(value)
            rows.append(row)

        return rows
    else:
        # All scalar values or mixed - return as single row
        row = [v for v in extracted_values]
        return [row]


def _get_client(context: Context = None) -> SuperFakturaClient:
    """SuperFaktura client from the environment (stdio: one account per server process)."""
    email = os.getenv("SUPERFAKTURA_EMAIL")
    api_key = os.getenv("SUPERFAKTURA_API_KEY")
    if not email or not api_key:
        raise ValueError(
            "SuperFaktura credentials required: set SUPERFAKTURA_EMAIL and SUPERFAKTURA_API_KEY "
            "(SuperFaktura > Tools > API) in the MCP server's env."
        )
    return SuperFakturaClient(
        email=email,
        api_key=api_key,
        company_id=os.getenv("SUPERFAKTURA_COMPANY_ID"),
        country=os.getenv("SUPERFAKTURA_COUNTRY"),
    )


@mcp.tool(annotations=_ann("create_invoice"))
def create_invoice(
    client_id: int,
    name: str,
    invoice_items: List[Dict[str, Any]],
    issued_date: Optional[str] = None,
    due_date: Optional[str] = None,
    variable_symbol: Optional[str] = None,
    # Common optional fields
    payment_type: Optional[str] = None,
    order_no: Optional[str] = None,
    comment: Optional[str] = None,
    header_comment: Optional[str] = None,
    internal_comment: Optional[str] = None,
    delivery_date: Optional[str] = None,
    delivery_type: Optional[str] = None,
    constant_symbol: Optional[str] = None,
    specific_symbol: Optional[str] = None,
    already_paid: Optional[int] = None,
    paydate: Optional[str] = None,
    discount: Optional[float] = None,
    discount_total: Optional[float] = None,
    invoice_currency: Optional[str] = None,
    # Advanced optional fields
    issued_by: Optional[str] = None,
    issued_by_email: Optional[str] = None,
    issued_by_phone: Optional[str] = None,
    issued_by_web: Optional[str] = None,
    invoice_no_formatted: Optional[str] = None,
    add_rounding_item: Optional[int] = None,
    bank_accounts: Optional[List[Dict[str, str]]] = None,
    deposit: Optional[float] = None,
    estimate_id: Optional[int] = None,
    logo_id: Optional[int] = None,
    mark_sent: Optional[int] = None,
    mark_sent_message: Optional[str] = None,
    mark_sent_subject: Optional[str] = None,
    parent_id: Optional[int] = None,
    proforma_id: Optional[str] = None,
    rounding: Optional[str] = None,
    sequence_id: Optional[int] = None,
    tax_document: Optional[int] = None,
    type: Optional[str] = None,
    vat_transfer: Optional[int] = None,
    # Advanced objects
    invoice_setting: Optional[Dict[str, Any]] = None,
    invoice_extra: Optional[Dict[str, Any]] = None,
    my_data: Optional[Dict[str, Any]] = None,
context: Context = None,
) -> Dict[str, Any]:
    """
    Create a new invoice in SuperFaktura with comprehensive options.

    Args:
        client_id: ID of the client to invoice
        name: Invoice name/description
        invoice_items: List of items, each with keys: name, description, unit_price (price per unit WITHOUT VAT),
                      quantity, tax (VAT percent, e.g. 23 or 0), and optional unit, discount, AccountingDetail
        issued_date: Issue date (YYYY-MM-DD), defaults to today
        due_date: Due date (YYYY-MM-DD), defaults to issued_date
        variable_symbol: Variable symbol for payment identification
        payment_type: Payment type (transfer, cash, card, paypal, etc.)
        order_no: Order number
        comment: Public comment
        header_comment: Comment above invoice items
        internal_comment: Internal comment (not displayed on invoice)
        delivery_date: Delivery date (YYYY-MM-DD)
        delivery_type: Delivery type
        constant_symbol: Constant symbol
        specific_symbol: Specific symbol
        already_paid: Is invoice already paid? (0=no, 1=yes)
        paydate: Payment date (YYYY-MM-DD)
        discount: Discount in percent
        discount_total: Nominal discount (only if discount not set)
        invoice_currency: Currency code (EUR, USD, CZK, etc.)
        issued_by: Who issued invoice (person name)
        issued_by_email: Issuer email
        issued_by_phone: Issuer phone
        issued_by_web: Website displayed on invoice
        invoice_no_formatted: Custom invoice number
        add_rounding_item: Add rounding item (0=no, 1=yes)
        bank_accounts: List of bank accounts [{"bank_name": "", "iban": "", "swift": ""}]
        deposit: Deposit amount paid
        estimate_id: Estimate ID this invoice is based on
        logo_id: Logo ID to use
        mark_sent: Mark invoice as sent via email (0=no, 1=yes)
        mark_sent_message: Email message for mark_sent
        mark_sent_subject: Email subject for mark_sent
        parent_id: Invoice ID to cancel
        proforma_id: Proforma invoice IDs (comma-separated for multiple)
        rounding: Rounding type (item, item_ext, total, etc.)
        sequence_id: Sequence ID
        tax_document: Is there a receipt? (0=no, 1=yes)
        type: Invoice type (regular, proforma, estimate, cancel, delivery, etc.)
        vat_transfer: VAT reverse charge (0=no, 1=yes)
        invoice_setting: Dict with keys: language, signature, payment_info, online_payment, bysquare, paypal
        invoice_extra: Dict with keys like: pickup_point_id
        my_data: Dict to override company data (address, company_name, city, country_id, dic, ic_dph, zip, etc.)

    Returns:
        Invoice creation response with invoice ID and details
    """
    if not issued_date:
        issued_date = datetime.now().strftime("%Y-%m-%d")
    if not due_date:
        due_date = issued_date

    invoice_data: Dict[str, Any] = {
        "Invoice": {
            "client_id": client_id,
            "name": name,
            "created": issued_date,
            "due": due_date,
        },
        "InvoiceItem": invoice_items,
    }

    # Add optional fields to Invoice object
    invoice_obj = invoice_data["Invoice"]

    if variable_symbol:
        invoice_obj["variable"] = variable_symbol
    if payment_type:
        invoice_obj["payment_type"] = payment_type
    if order_no:
        invoice_obj["order_no"] = order_no
    if comment:
        invoice_obj["comment"] = comment
    if header_comment:
        invoice_obj["header_comment"] = header_comment
    if internal_comment:
        invoice_obj["internal_comment"] = internal_comment
    if delivery_date:
        invoice_obj["delivery"] = delivery_date
    if delivery_type:
        invoice_obj["delivery_type"] = delivery_type
    if constant_symbol:
        invoice_obj["constant"] = constant_symbol
    if specific_symbol:
        invoice_obj["specific"] = specific_symbol
    if already_paid is not None:
        invoice_obj["already_paid"] = already_paid
    if paydate:
        invoice_obj["paydate"] = paydate
    if discount is not None:
        invoice_obj["discount"] = discount
    if discount_total is not None:
        invoice_obj["discount_total"] = discount_total
    if invoice_currency:
        invoice_obj["invoice_currency"] = invoice_currency
    if issued_by:
        invoice_obj["issued_by"] = issued_by
    if issued_by_email:
        invoice_obj["issued_by_email"] = issued_by_email
    if issued_by_phone:
        invoice_obj["issued_by_phone"] = issued_by_phone
    if issued_by_web:
        invoice_obj["issued_by_web"] = issued_by_web
    if invoice_no_formatted:
        invoice_obj["invoice_no_formatted"] = invoice_no_formatted
    if add_rounding_item is not None:
        invoice_obj["add_rounding_item"] = add_rounding_item
    if bank_accounts:
        invoice_obj["bank_accounts"] = bank_accounts
    if deposit is not None:
        invoice_obj["deposit"] = deposit
    if estimate_id:
        invoice_obj["estimate_id"] = estimate_id
    if logo_id:
        invoice_obj["logo_id"] = logo_id
    if mark_sent is not None:
        invoice_obj["mark_sent"] = mark_sent
    if mark_sent_message:
        invoice_obj["mark_sent_message"] = mark_sent_message
    if mark_sent_subject:
        invoice_obj["mark_sent_subject"] = mark_sent_subject
    if parent_id:
        invoice_obj["parent_id"] = parent_id
    if proforma_id:
        invoice_obj["proforma_id"] = proforma_id
    if rounding:
        invoice_obj["rounding"] = rounding
    if sequence_id:
        invoice_obj["sequence_id"] = sequence_id
    if tax_document is not None:
        invoice_obj["tax_document"] = tax_document
    if type:
        invoice_obj["type"] = type
    if vat_transfer is not None:
        invoice_obj["vat_transfer"] = vat_transfer

    # Add advanced objects
    if invoice_setting:
        invoice_data["InvoiceSetting"] = invoice_setting
    if invoice_extra:
        invoice_data["InvoiceExtra"] = invoice_extra
    if my_data:
        invoice_data["MyData"] = my_data

    return _get_client(context).post("invoices/create", invoice_data)


@mcp.tool(annotations=_ann("list_invoices"))
def list_invoices(
    page: int = 1,
    per_page: int = 50,
    listinfo: int = 1,
    direction: str = "DESC",
    sort: str = "regular_count",
    type: Optional[str] = None,
    status: Optional[str] = None,
    client_id: Optional[int] = None,
    created_since: Optional[str] = None,
    created_to: Optional[str] = None,
    modified_since: Optional[str] = None,
    modified_to: Optional[str] = None,
    delivery_since: Optional[str] = None,
    delivery_to: Optional[str] = None,
    paydate_since: Optional[str] = None,
    paydate_to: Optional[str] = None,
    amount_from: Optional[float] = None,
    amount_to: Optional[float] = None,
    payment_type: Optional[str] = None,
    delivery_type: Optional[str] = None,
    invoice_no_formatted: Optional[str] = None,
    order_no: Optional[str] = None,
    variable: Optional[str] = None,
    search: Optional[str] = None,
    tag: Optional[int] = None,
    ignore: Optional[str] = None,
    fields_filter: Optional[List[str]] = None,
context: Context = None,
) -> Any:
    """
    List invoices with comprehensive filtering and sorting.

    Args:
        page: Page number for pagination
        per_page: Number of results per page (max 200)
        listinfo: Show meta data about result (0=no, 1=yes)
        direction: Sorting direction (ASC or DESC)
        sort: Attribute to sort by (e.g., 'regular_count', 'created', 'amount')
        type: Document type filter (proforma, regular, etc.). Use | for multiple (e.g., 'regular|proforma')
        status: Filter by status (1=issued, 2=partially paid, 3=paid, 99=overdue). Use | for multiple
        client_id: Filter by client ID
        created_since: Creation date from (YYYY-MM-DD, requires created:3)
        created_to: Creation date to (YYYY-MM-DD, requires created:3)
        modified_since: Last modification date from (YYYY-MM-DD, requires modified:3)
        modified_to: Last modification date to (YYYY-MM-DD, requires modified:3)
        delivery_since: Delivery date from (YYYY-MM-DD, requires delivery:3)
        delivery_to: Delivery date to (YYYY-MM-DD, requires delivery:3)
        paydate_since: Payment date from (YYYY-MM-DD, requires paydate:3)
        paydate_to: Payment date to (YYYY-MM-DD, requires paydate:3)
        amount_from: Minimum invoice amount
        amount_to: Maximum invoice amount
        payment_type: Payment type filter (transfer, cash, card, etc.). Use | for multiple
        delivery_type: Delivery type filter. Use | for multiple
        invoice_no_formatted: Search by formatted invoice number
        order_no: Search by order number
        variable: Search by variable symbol
        search: Plain-text search term (the tool encodes it for the API)
        tag: Filter by tag ID
        ignore: Invoice IDs to exclude. Use | for multiple (e.g., '1|2|3')
        fields_filter: List of field paths to extract as array of arrays (rows)
                      - None (default): return all fields unchanged
                      - []: return empty array
                      - ["field1", "field2"]: return only specified fields as array of arrays
                      Examples:
                        - None -> {full response with all fields}
                        - [] -> []
                        - ["items.Invoice.id", "items.Invoice.name"] -> [[1, "Invoice A"], [2, "Invoice B"], ...]
                        - ["items.Invoice.total", "items.Client.name"] -> [[100.50, "Company A"], [250.00, "Company B"], ...]
                        - ["itemCount", "pageCount"] -> [[42, 3]]

    Returns:
        List of invoices with pagination info and metadata (if fields_filter is None), or array of arrays if fields_filter is specified
    """
    # Validate per_page max
    if per_page > 200:
        per_page = 200

    params = [
        _seg("page", page),
        _seg("per_page", per_page),
        _seg("listinfo", listinfo),
    ]

    # Time-based filters - add BEFORE sort to avoid URL parsing conflicts
    # when sort field name matches a filter field name (e.g., sort:delivery vs delivery:3)
    if created_since or created_to:
        params.append("created:3")
        if created_since:
            params.append(_seg("created_since", created_since))
        if created_to:
            params.append(_seg("created_to", created_to))

    if modified_since or modified_to:
        params.append("modified:3")
        if modified_since:
            params.append(_seg("modified_since", modified_since))
        if modified_to:
            params.append(_seg("modified_to", modified_to))

    if delivery_since or delivery_to:
        params.append("delivery:3")
        if delivery_since:
            params.append(_seg("delivery_since", delivery_since))
        if delivery_to:
            params.append(_seg("delivery_to", delivery_to))

    if paydate_since or paydate_to:
        params.append("paydate:3")
        if paydate_since:
            params.append(_seg("paydate_since", paydate_since))
        if paydate_to:
            params.append(_seg("paydate_to", paydate_to))

    # Add sort after date filters to avoid conflicts
    params.append(_seg("direction", direction))
    params.append(_seg("sort", sort))

    if type:
        params.append(_seg("type", type))
    if status:
        params.append(_seg("status", status))
    if client_id:
        params.append(_seg("client_id", client_id))

    # Amount filters
    if amount_from is not None:
        params.append(_seg("amount_from", amount_from))
    if amount_to is not None:
        params.append(_seg("amount_to", amount_to))

    # Other filters
    if payment_type:
        params.append(_seg("payment_type", payment_type))
    if delivery_type:
        params.append(_seg("delivery_type", delivery_type))
    if invoice_no_formatted and "/" in invoice_no_formatted:
        # SuperFaktura does not match an encoded slash in this path filter (sandbox, 25. 11. 2026);
        # its full-text search finds the number, so use that instead
        if search:
            return {"error": "Use either search or an invoice_no_formatted containing '/', not both.", "status": "failed"}
        search = invoice_no_formatted
    elif invoice_no_formatted:
        params.append(_seg("invoice_no_formatted", invoice_no_formatted))
    if order_no:
        params.append(_seg("order_no", order_no))
    if variable:
        params.append(_seg("variable", variable))
    if search:
        params.append(_seg("search", _sf_b64(search)))
    if tag:
        params.append(_seg("tag", tag))
    if ignore:
        params.append(_seg("ignore", ignore))

    endpoint = f"invoices/index.json/{'/'.join(params)}"
    response = _get_client(context).get(endpoint)
    return _apply_fields_filter(response, fields_filter)


@mcp.tool(annotations=_ann("get_invoice"))
def get_invoice(
    invoice_id: int,
    fields_filter: Optional[List[str]] = None,
    context: Context = None,
) -> Any:
    """
    Get detailed information about a specific invoice.

    Args:
        invoice_id: ID of the invoice to retrieve
        fields_filter: List of field paths to extract as array of arrays (rows)
                      - None (default): return all fields unchanged
                      - []: return empty array
                      - ["field1", "field2"]: return only specified fields as array of arrays
                      Examples:
                        - None -> {full invoice response with all fields}
                        - [] -> []
                        - ["Invoice.id", "Invoice.name"] -> [[123, "My Invoice"]]
                        - ["Invoice.total", "Client.name"] -> [[500.00, "ACME Corp"]]
                        - ["InvoiceItem.name", "InvoiceItem.unit_price"] -> [["Item A", 10.00], ["Item B", 20.00], ...]

    Returns:
        Invoice details including items, client info, and payment status (if fields_filter is None), or array of arrays if fields_filter is specified
    """
    response = _get_client(context).get(f"invoices/view/{invoice_id}.json")
    return _apply_fields_filter(response, fields_filter)


@mcp.tool(annotations=_ann("send_invoice"))
def send_invoice(invoice_id: int, email: str,
pdf_language: Optional[str] = None,
context: Context = None,
) -> Dict[str, Any]:
    """Sends a real email to the customer. Confirm with the user first.

    Emails the invoice PDF to `email` (required, never guessed; SuperFaktura limit: 100 emails per hour).

    Args:
        invoice_id: ID of the invoice to send
        email: Recipient address, as confirmed by the user
        pdf_language: Optional PDF language (eng, slo, cze, deu, ...)

    Returns:
        Response indicating if email was sent successfully
    """
    if not email or "@" not in email:
        return {"error": "A recipient email is required.", "status": "failed"}
    data: Dict[str, Any] = {"Email": {"invoice_id": invoice_id, "to": email}}
    if pdf_language:
        lang = _language(pdf_language)
        if not lang:
            return _bad_language(pdf_language)
        data["Email"]["pdf_language"] = lang

    return _get_client(context).post("invoices/send", data)


@mcp.tool(annotations=_ann("mark_invoice_paid"))
def mark_invoice_paid(
    invoice_id: int, amount: float, payment_date: Optional[str] = None,
    payment_type: str = "transfer", currency: Optional[str] = None,
    context: Context = None,
) -> Dict[str, Any]:
    """
    Record a payment on an invoice (partial or full).

    Args:
        invoice_id: ID of the invoice
        amount: Amount paid
        payment_date: Date of the payment (YYYY-MM-DD), defaults to today
        payment_type: transfer (default), cash, card, cod, paypal, other, ... (docs: Value lists > Payment types)
        currency: Currency of the payment; defaults to the invoice's currency

    Returns:
        Payment recording response
    """
    sf = _get_client(context)
    if not payment_date:
        payment_date = datetime.now().strftime("%Y-%m-%d")
    if not currency:
        invoice, err = _view_invoice(sf, invoice_id)
        if err:
            return err
        currency = invoice.get("invoice_currency")

    # docs name the field `date`; the API response and stored payment use `created`, so send both
    payment = {"invoice_id": invoice_id, "amount": amount, "payment_type": payment_type,
               "date": payment_date, "created": payment_date}
    if currency:
        payment["currency"] = currency
    return sf.post("invoice_payments/add/ajax:1/api:1", {"InvoicePayment": payment})


@mcp.tool(annotations=_ann("create_client"))
def create_client(
    name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    address: Optional[str] = None,
    city: Optional[str] = None,
    zip_code: Optional[str] = None,
    country: Optional[str] = None,
    country_id: Optional[int] = None,
    ico: Optional[str] = None,
    dic: Optional[str] = None,
    ic_dph: Optional[str] = None,
    # Extended fields
    bank_account: Optional[str] = None,
    bank_code: Optional[str] = None,
    iban: Optional[str] = None,
    swift: Optional[str] = None,
    fax: Optional[str] = None,
    comment: Optional[str] = None,
    currency: Optional[str] = None,
    default_variable: Optional[str] = None,
    discount: Optional[float] = None,
    due_date: Optional[int] = None,
    uuid: Optional[str] = None,
    # Delivery address fields
    delivery_name: Optional[str] = None,
    delivery_address: Optional[str] = None,
    delivery_city: Optional[str] = None,
    delivery_zip: Optional[str] = None,
    delivery_country: Optional[str] = None,
    delivery_country_id: Optional[int] = None,
    delivery_phone: Optional[str] = None,
    # Other fields
    match_address: Optional[int] = None,
    update: Optional[bool] = None,
    tags: Optional[str] = None,

context: Context = None,
) -> Dict[str, Any]:
    """
    Create a new client in SuperFaktura with comprehensive options.

    Args:
        name: Client/company name (required)
        email: Client email address
        phone: Client phone number
        address: Street address
        city: City
        zip_code: ZIP/postal code
        country: Custom country name
        country_id: Country ID (see SuperFaktura docs for country list)
        ico: Company registration number (IČO)
        dic: Tax ID number (DIČ)
        ic_dph: VAT ID (IČ DPH)
        bank_account: Bank account number
        bank_code: Bank code
        iban: IBAN
        swift: SWIFT code
        fax: Fax number
        comment: Note for this client
        currency: Default currency for this client (EUR, USD, CZK, etc.)
        default_variable: Default variable symbol for documents
        discount: Default discount percentage for this client
        due_date: Default due days for documents
        uuid: Custom unique identifier
        delivery_name: Delivery recipient name
        delivery_address: Delivery street address
        delivery_city: Delivery city
        delivery_zip: Delivery ZIP code
        delivery_country: Custom delivery country name
        delivery_country_id: Delivery country ID
        delivery_phone: Delivery phone number
        match_address: Include address in client searching (0=no, 1=yes)
        update: Also update client in addressbook
        tags: Tags for this client (see SuperFaktura docs for tag format)

    Returns:
        Client creation response with client ID
    """
    if not name or not name.strip():
        # SuperFaktura answers an empty name with {"error": 1, "error_message": []}
        return {"error": "Client name is required.", "status": "failed"}
    client_data: Dict[str, Any] = {"Client": {"name": name}}

    client_obj = client_data["Client"]

    if email:
        client_obj["email"] = email
    if phone:
        client_obj["phone"] = phone
    if address:
        client_obj["address"] = address
    if city:
        client_obj["city"] = city
    if zip_code:
        client_obj["zip"] = zip_code
    if country:
        client_obj["country"] = country
    if country_id:
        client_obj["country_id"] = country_id
    if ico:
        client_obj["ico"] = ico
    if dic:
        client_obj["dic"] = dic
    if ic_dph:
        client_obj["ic_dph"] = ic_dph
    if bank_account:
        client_obj["bank_account"] = bank_account
    if bank_code:
        client_obj["bank_code"] = bank_code
    if iban:
        client_obj["iban"] = iban
    if swift:
        client_obj["swift"] = swift
    if fax:
        client_obj["fax"] = fax
    if comment:
        client_obj["comment"] = comment
    if currency:
        client_obj["currency"] = currency
    if default_variable:
        client_obj["default_variable"] = default_variable
    if discount is not None:
        client_obj["discount"] = discount
    if due_date is not None:
        client_obj["due_date"] = due_date
    if uuid:
        client_obj["uuid"] = uuid
    if delivery_name:
        client_obj["delivery_name"] = delivery_name
    if delivery_address:
        client_obj["delivery_address"] = delivery_address
    if delivery_city:
        client_obj["delivery_city"] = delivery_city
    if delivery_zip:
        client_obj["delivery_zip"] = delivery_zip
    if delivery_country:
        client_obj["delivery_country"] = delivery_country
    if delivery_country_id:
        client_obj["delivery_country_id"] = delivery_country_id
    if delivery_phone:
        client_obj["delivery_phone"] = delivery_phone
    if match_address is not None:
        client_obj["match_address"] = match_address
    if update is not None:
        client_obj["update"] = update
    if tags:
        client_obj["tags"] = tags

    return _get_client(context).post("clients/create", client_data)


@mcp.tool(annotations=_ann("list_clients"))
def list_clients(
    page: int = 1,
    per_page: int = 50,
    listinfo: int = 1,
    direction: str = "DESC",
    sort: str = "regular_count",
    char_filter: Optional[str] = None,
    search: Optional[str] = None,
    search_uuid: Optional[str] = None,
    tag: Optional[int] = None,
    created_since: Optional[str] = None,
    created_to: Optional[str] = None,
    modified_since: Optional[str] = None,
    modified_to: Optional[str] = None,
    fields_filter: Optional[List[str]] = None,
context: Context = None,
) -> Any:
    """
    List all clients with comprehensive filtering and sorting.

    Args:
        page: Page number for pagination
        per_page: Number of results per page
        listinfo: Show meta data about result (0=no, 1=yes)
        direction: Sorting direction (ASC or DESC)
        sort: Attribute to sort by
        char_filter: Filter by first letter of client name (use # for non-letters)
        search: Plain-text search (the tool encodes it); searches name, ICO, DIC, IC_DPH, bank_account, email, address, city, zip, state, country, phone, fax, comment, tags, UUID)
        search_uuid: Search by exact UUID
        tag: Filter by tag ID
        created_since: Creation date from (YYYY-MM-DD, requires created:3)
        created_to: Creation date to (YYYY-MM-DD, requires created:3)
        modified_since: Last modification date from (YYYY-MM-DD, requires modified:3)
        modified_to: Last modification date to (YYYY-MM-DD, requires modified:3)
        fields_filter: List of field paths to extract as array of arrays (rows)
                      - None (default): return all fields unchanged
                      - []: return empty array
                      - ["field1", "field2"]: return only specified fields as array of arrays
                      Examples:
                        - None -> {full response with all fields}
                        - [] -> []
                        - ["items.Client.name", "items.Client.email"] -> [["ACME Corp", "info@acme.com"], ["Company B", "b@example.com"], ...]
                        - ["items.Client.ico", "items.Client.dic"] -> [["12345678", "CZ12345678"], ...]
                        - ["itemCount", "pageCount"] -> [[15, 1]]

    Returns:
        List of clients with pagination info and metadata (if fields_filter is None), or array of arrays if fields_filter is specified
    """
    params = [
        _seg("page", page),
        _seg("per_page", per_page),
        _seg("listinfo", listinfo),
    ]

    # Time-based filters - add BEFORE sort to avoid URL parsing conflicts
    # when sort field name matches a filter field name (e.g., sort:created vs created:3)
    if created_since or created_to:
        params.append("created:3")
        if created_since:
            params.append(_seg("created_since", created_since))
        if created_to:
            params.append(_seg("created_to", created_to))

    if modified_since or modified_to:
        params.append("modified:3")
        if modified_since:
            params.append(_seg("modified_since", modified_since))
        if modified_to:
            params.append(_seg("modified_to", modified_to))

    # Add sort after date filters to avoid conflicts
    params.append(_seg("direction", direction))
    params.append(_seg("sort", sort))

    if char_filter:
        params.append(_seg("char_filter", char_filter))
    if search:
        params.append(_seg("search", _sf_b64(search)))
    if search_uuid:
        params.append(_seg("search_uuid", search_uuid))
    if tag:
        params.append(_seg("tag", tag))

    endpoint = f"clients/index.json/{'/'.join(params)}"
    response = _get_client(context).get(endpoint)
    return _apply_fields_filter(response, fields_filter)


@mcp.tool(annotations=_ann("get_client"))
def get_client(
    client_id: int,
    fields_filter: Optional[List[str]] = None,
    context: Context = None,
) -> Any:
    """
    Get detailed information about a specific client.

    Args:
        client_id: ID of the client to retrieve
        fields_filter: List of field paths to extract as array of arrays (rows)
                      - None (default): return all fields unchanged
                      - []: return empty array
                      - ["field1", "field2"]: return only specified fields as array of arrays
                      Examples:
                        - None -> {full client response with all fields}
                        - [] -> []
                        - ["Client.name", "Client.email"] -> [["ACME Corp", "info@acme.com"]]
                        - ["Client.ico", "Client.dic", "Client.city"] -> [["12345678", "CZ12345678", "Prague"]]

    Returns:
        Client details including contact information and invoice history (if fields_filter is None), or array of arrays if fields_filter is specified
    """
    response = _get_client(context).get(f"clients/view/{client_id}.json")
    return _apply_fields_filter(response, fields_filter)


@mcp.tool(annotations=_ann("update_client"))
def update_client(client_id: int, updates: Dict[str, Any], context: Context = None,
) -> Dict[str, Any]:
    """
    Update client information.

    Args:
        client_id: ID of the client to update
        updates: Dictionary of fields to update (name, email, phone, address, etc.)

    Returns:
        Update response
    """
    client_data = {"Client": {"id": client_id, **updates}}
    return _get_client(context).patch(f"clients/edit/{client_id}", client_data)


@mcp.tool(annotations=_ann("create_expense"))
def create_expense(
    name: str,
    amount: Optional[float] = None,
    expense_date: Optional[str] = None,
    # Basic fields
    vat: Optional[float] = None,
    currency: Optional[str] = None,
    expense_category_id: Optional[int] = None,
    comment: Optional[str] = None,
    variable_symbol: Optional[str] = None,
    constant_symbol: Optional[str] = None,
    specific_symbol: Optional[str] = None,
    # Multiple VAT rates (for version: basic)
    amount2: Optional[float] = None,
    vat2: Optional[float] = None,
    amount3: Optional[float] = None,
    vat3: Optional[float] = None,
    # Advanced fields
    client_id: Optional[int] = None,
    already_paid: Optional[int] = None,
    delivery_date: Optional[str] = None,
    due_date: Optional[str] = None,
    document_number: Optional[str] = None,
    payment_type: Optional[str] = None,
    taxable_supply: Optional[str] = None,
    type: Optional[str] = None,
    version: Optional[str] = None,
    # File attachment
    attachment: Optional[str] = None,
    # Advanced objects
    expense_items: Optional[List[Dict[str, Any]]] = None,
    expense_extra: Optional[Dict[str, Any]] = None,
    client_data: Optional[Dict[str, Any]] = None,
    context: Context = None,
) -> Dict[str, Any]:
    """
    Create a new expense record with comprehensive options.

    Args:
        name: Expense name (required)
        amount: Amount of money without VAT (for version: basic)
        expense_date: Expense date (YYYY-MM-DD), defaults to today
        vat: VAT percentage (for version: basic)
        currency: Currency code (EUR, USD, CZK, etc.)
        expense_category_id: Expense category ID
        comment: Comment/note
        variable_symbol: Variable symbol
        constant_symbol: Constant symbol
        specific_symbol: Specific symbol
        amount2: Amount without VAT for second VAT rate (version: basic)
        vat2: Second VAT percentage (version: basic)
        amount3: Amount without VAT for third VAT rate (version: basic)
        vat3: Third VAT percentage (version: basic)
        client_id: Client ID
        already_paid: Is expense already paid? (0=no, 1=yes)
        delivery_date: Delivery date (YYYY-MM-DD)
        due_date: Due date (YYYY-MM-DD)
        document_number: Document number (invoice number, bill number, etc.)
        payment_type: Payment type (transfer, cash, card, etc.)
        taxable_supply: Date of taxable transaction (YYYY-MM-DD)
        type: Expense type (invoice, bill, etc.)
        version: Expense version - 'basic' (without items, only VAT rates) or 'items' (with items)
        attachment: Base64 encoded file (max 4MB, allowed: jpg, jpeg, png, tif, tiff, gif, pdf, tmp, xls, xlsx, ods, doc, docx, xml, csv, msg, heic, isdoc)
        expense_items: List of expense items (each with: name, description, unit_price, quantity, tax). Used when version='items'
        expense_extra: Dict with keys like: vat_transfer (0=no, 1=yes)
        client_data: Dict to create/update client (name, ico, dic, etc.)

    Returns:
        Expense creation response with expense ID
    """
    if not expense_date:
        expense_date = datetime.now().strftime("%Y-%m-%d")

    expense_data: Dict[str, Any] = {
        "Expense": {
            "name": name,
            "created": expense_date,
        }
    }

    expense_obj = expense_data["Expense"]

    if amount is not None:
        expense_obj["amount"] = amount
    if vat is not None:
        expense_obj["vat"] = vat
    if currency:
        expense_obj["currency"] = currency
    if expense_category_id:
        expense_obj["expense_category_id"] = expense_category_id
    if comment:
        expense_obj["comment"] = comment
    if variable_symbol:
        expense_obj["variable"] = variable_symbol
    if constant_symbol:
        expense_obj["constant"] = constant_symbol
    if specific_symbol:
        expense_obj["specific"] = specific_symbol
    if amount2 is not None:
        expense_obj["amount2"] = amount2
    if vat2 is not None:
        expense_obj["vat2"] = vat2
    if amount3 is not None:
        expense_obj["amount3"] = amount3
    if vat3 is not None:
        expense_obj["vat3"] = vat3
    if client_id:
        expense_obj["client_id"] = client_id
    if already_paid is not None:
        expense_obj["already_paid"] = already_paid
    if delivery_date:
        expense_obj["delivery"] = delivery_date
    if due_date:
        expense_obj["due"] = due_date
    if document_number:
        expense_obj["document_number"] = document_number
    if payment_type:
        expense_obj["payment_type"] = payment_type
    if taxable_supply:
        expense_obj["taxable_supply"] = taxable_supply
    if type:
        expense_obj["type"] = type
    if version:
        expense_obj["version"] = version
    if attachment:
        expense_obj["attachment"] = attachment

    # Add advanced objects
    if expense_items:
        expense_data["ExpenseItem"] = expense_items
    if expense_extra:
        expense_data["ExpenseExtra"] = expense_extra
    if client_data:
        expense_data["Client"] = client_data

    return _get_client(context).post("expenses/add", expense_data)


@mcp.tool(annotations=_ann("list_expenses"))
def list_expenses(
    page: int = 1,
    per_page: int = 50,
    listinfo: int = 1,
    direction: str = "DESC",
    sort: str = "regular_count",
    amount_from: Optional[float] = None,
    amount_to: Optional[float] = None,
    category: Optional[int] = None,
    client_id: Optional[int] = None,
    created_since: Optional[str] = None,
    created_to: Optional[str] = None,
    modified_since: Optional[str] = None,
    modified_to: Optional[str] = None,
    delivery_since: Optional[str] = None,
    delivery_to: Optional[str] = None,
    due: Optional[str] = None,
    payment_type: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    type: Optional[str] = None,
    fields_filter: Optional[List[str]] = None,
context: Context = None,
) -> Any:
    """
    List expenses with comprehensive filtering and sorting.

    Args:
        page: Page number for pagination
        per_page: Number of results per page (max 100)
        listinfo: Show meta data about result (0=no, 1=yes)
        direction: Sorting direction (ASC or DESC)
        sort: Attribute to sort by
        amount_from: Minimum expense amount
        amount_to: Maximum expense amount
        category: Expense category ID
        client_id: Filter by client ID
        created_since: Creation date from (YYYY-MM-DD, requires created:3)
        created_to: Creation date to (YYYY-MM-DD, requires created:3)
        modified_since: Last modification date from (YYYY-MM-DD, requires modified:3)
        modified_to: Last modification date to (YYYY-MM-DD, requires modified:3)
        delivery_since: Delivery date from (YYYY-MM-DD, requires delivery:3)
        delivery_to: Delivery date to (YYYY-MM-DD, requires delivery:3)
        due: Due date (YYYY-MM-DD)
        payment_type: Payment type filter (see SuperFaktura docs for valid values)
        search: Plain-text search term (the tool encodes it for the API)
        status: Expense status filter. Use | for multiple (e.g., '1|2')
        type: Expense type filter
        fields_filter: List of field paths to extract as array of arrays (rows)
                      - None (default): return all fields unchanged
                      - []: return empty array
                      - ["field1", "field2"]: return only specified fields as array of arrays
                      Examples:
                        - None -> {full response with all fields}
                        - [] -> []
                        - ["items.Expense.name", "items.Expense.amount"] -> [["Office supplies", 150.00], ["Software license", 99.00], ...]
                        - ["items.Expense.expense_date", "items.Client.name"] -> [["2025-01-15", "Supplier A"], ...]
                        - ["itemCount", "pageCount"] -> [[8, 1]]

    Returns:
        List of expenses with pagination info and metadata (if fields_filter is None), or array of arrays if fields_filter is specified
    """
    # Validate per_page max
    if per_page > 100:
        per_page = 100

    params = [
        _seg("page", page),
        _seg("per_page", per_page),
        _seg("listinfo", listinfo),
    ]

    # Time-based filters - add BEFORE sort to avoid URL parsing conflicts
    # when sort field name matches a filter field name (e.g., sort:delivery vs delivery:3)
    if created_since or created_to:
        params.append("created:3")
        if created_since:
            params.append(_seg("created_since", created_since))
        if created_to:
            params.append(_seg("created_to", created_to))

    if modified_since or modified_to:
        params.append("modified:3")
        if modified_since:
            params.append(_seg("modified_since", modified_since))
        if modified_to:
            params.append(_seg("modified_to", modified_to))

    if delivery_since or delivery_to:
        params.append("delivery:3")
        if delivery_since:
            params.append(_seg("delivery_since", delivery_since))
        if delivery_to:
            params.append(_seg("delivery_to", delivery_to))

    # Add sort after date filters to avoid conflicts
    params.append(_seg("direction", direction))
    params.append(_seg("sort", sort))

    if amount_from is not None:
        params.append(_seg("amount_from", amount_from))
    if amount_to is not None:
        params.append(_seg("amount_to", amount_to))
    if category:
        params.append(_seg("category", category))
    if client_id:
        params.append(_seg("client_id", client_id))

    if due:
        params.append(_seg("due", due))
    if payment_type:
        params.append(_seg("payment_type", payment_type))
    if search:
        params.append(_seg("search", _sf_b64(search)))
    if status:
        params.append(_seg("status", status))
    if type:
        params.append(_seg("type", type))

    endpoint = f"expenses/index.json/{'/'.join(params)}"
    response = _get_client(context).get(endpoint)
    return _apply_fields_filter(response, fields_filter)


@mcp.tool(annotations=_ann("get_expense"))
def get_expense(
    expense_id: int,
    fields_filter: Optional[List[str]] = None,
    context: Context = None,
) -> Any:
    """
    Get detailed information about a specific expense.

    Args:
        expense_id: ID of the expense to retrieve
        fields_filter: List of field paths to extract as array of arrays (rows)
                      - None (default): return all fields unchanged
                      - []: return empty array
                      - ["field1", "field2"]: return only specified fields as array of arrays
                      Examples:
                        - None -> {full expense response with all fields}
                        - [] -> []
                        - ["Expense.name", "Expense.amount"] -> [["Office supplies", 150.00]]
                        - ["ExpenseItem.name", "ExpenseItem.unit_price"] -> [["Paper", 10.00], ["Pens", 5.00], ...]
                        - ["Expense.expense_date", "Client.name"] -> [["2025-01-15", "Supplier A"]]

    Returns:
        Expense details (if fields_filter is None), or array of arrays if fields_filter is specified
    """
    response = _get_client(context).get(f"expenses/view/{expense_id}.json")
    return _apply_fields_filter(response, fields_filter)


# ============================================================================
# Additional Invoice Operations
# ============================================================================


@mcp.tool(annotations=_ann("edit_invoice"))
def edit_invoice(invoice_id: int, updates: Dict[str, Any], context: Context = None,
) -> Dict[str, Any]:
    """
    Edit an existing invoice.

    Args:
        invoice_id: ID of the invoice to edit
        updates: Dictionary of invoice fields to update (same structure as create_invoice)

    Returns:
        Invoice update response
    """
    invoice_data = {"Invoice": {"id": invoice_id, **updates.get("Invoice", updates)}}

    # Support for updating items, settings, etc.
    if "InvoiceItem" in updates:
        invoice_data["InvoiceItem"] = updates["InvoiceItem"]
    if "InvoiceSetting" in updates:
        invoice_data["InvoiceSetting"] = updates["InvoiceSetting"]
    if "InvoiceExtra" in updates:
        invoice_data["InvoiceExtra"] = updates["InvoiceExtra"]
    if "Client" in updates:
        invoice_data["Client"] = updates["Client"]

    return _get_client(context).post("invoices/edit", invoice_data)


@mcp.tool(annotations=_ann("get_invoice_pdf"))
def get_invoice_pdf(invoice_id: int, language: Optional[str] = None,
context: Context = None,
) -> Dict[str, Any]:
    """
    Download the invoice PDF to a private file on the computer running this server.

    Args:
        invoice_id: ID of the invoice
        language: Optional language code (slo, cze, eng, deu, ...); default is the invoice's language

    Returns:
        {"path": local file path, "bytes": size, "note": where the file is}, or an error
    """
    import tempfile

    lang = None
    if language:
        lang = _language(language)
        if not lang:
            return _bad_language(language)
    sf = _get_client(context)
    invoice, err = _view_invoice(sf, invoice_id)
    if err:
        return err
    token = invoice.get("token")
    if not token:
        return {"error": f"Invoice {invoice_id} has no PDF token in the response.", "status": "failed", "response": invoice}

    # URL per the docs: /[{LANGUAGE}/]invoices/pdf/{INVOICE_ID}/token:{TOKEN}
    endpoint = f"invoices/pdf/{invoice_id}/" + _seg("token", token)
    if lang:
        endpoint = f"{lang}/{endpoint}"
    pdf, err = sf.get_bytes(endpoint)
    if err:
        return err
    if not pdf.startswith(b"%PDF"):
        return {"error": "SuperFaktura did not return a PDF.", "status": "failed"}

    # ponytail: a private temp file suits stdio (the server runs on the user's computer);
    # a hosted server would return an embedded resource instead.
    try:
        fd, path = tempfile.mkstemp(prefix=f"superfaktura-invoice-{invoice_id}-{lang or 'default'}-", suffix=".pdf")
        with os.fdopen(fd, "wb") as f:
            f.write(pdf)
    except OSError as e:
        return {"error": f"Could not save the PDF: {e}", "status": "failed"}
    return {"path": path, "bytes": len(pdf), "note": "Saved on this computer, readable only by your user."}


@mcp.tool(annotations=_ann("delete_invoice"))
def delete_invoice(invoice_id: int,
context: Context = None,
) -> Dict[str, Any]:
    """PERMANENT: deletes the invoice in SuperFaktura. Confirm with the user first.

    An invoice that was already issued to a customer should normally be corrected with a
    credit note (dobropis: create_invoice with type="cancel" and parent_id) instead.

    Args:
        invoice_id: ID of the invoice to delete

    Returns:
        Deletion response
    """
    return _get_client(context).get(f"invoices/delete/{invoice_id}")


@mcp.tool(annotations=_ann("set_invoice_language"))
def set_invoice_language(invoice_id: int, language: str,
context: Context = None,
) -> Dict[str, Any]:
    """
    Set invoice language.

    Args:
        invoice_id: ID of the invoice
        language: cze, deu, eng, hrv, hun, ita, nld, pol, rom, rus, slo, slv, spa, ukr

    Returns:
        Update response
    """
    lang = _language(language)
    if not lang:
        return _bad_language(language)
    return _get_client(context).get(f"invoices/setinvoicelanguage/{invoice_id}/" + _seg("lang", lang))


@mcp.tool(annotations=_ann("list_expense_categories"))
def list_expense_categories(context: Context = None) -> Any:
    """
    List expense categories (ids for create_expense's expense_category_id).

    Returns:
        List of expense categories
    """
    return _get_client(context).get("expenses/expense_categories")


@mcp.tool(annotations=_ann("list_tags"))
def list_tags(context: Context = None) -> Any:
    """
    List tags (ids for the tag filter of list_invoices, list_clients and list_expenses).

    Returns:
        List of tags
    """
    return _get_client(context).get("tags/index.json")


# ============================================================================
# Additional Client Operations
# ============================================================================


@mcp.tool(annotations=_ann("delete_client"))
def delete_client(client_id: int,
context: Context = None,
) -> Dict[str, Any]:
    """PERMANENT: deletes the client (contact) in SuperFaktura. Confirm with the user first.

    Args:
        client_id: ID of the client to delete

    Returns:
        Deletion response
    """
    return _get_client(context).delete(f"clients/delete/{client_id}")


# ============================================================================
# Additional Expense Operations
# ============================================================================


@mcp.tool(annotations=_ann("edit_expense"))
def edit_expense(expense_id: int, updates: Dict[str, Any], context: Context = None,
) -> Dict[str, Any]:
    """
    Edit an existing expense.

    Args:
        expense_id: ID of the expense to edit
        updates: Dictionary of expense fields to update (same structure as create_expense)

    Returns:
        Expense update response
    """
    expense_data = {"Expense": {"id": expense_id, **updates.get("Expense", updates)}}

    # Support for updating items, client, etc.
    if "ExpenseItem" in updates:
        expense_data["ExpenseItem"] = updates["ExpenseItem"]
    if "ExpenseExtra" in updates:
        expense_data["ExpenseExtra"] = updates["ExpenseExtra"]
    if "Client" in updates:
        expense_data["Client"] = updates["Client"]

    return _get_client(context).post("expenses/edit", expense_data)


@mcp.tool(annotations=_ann("delete_expense"))
def delete_expense(expense_id: int,
context: Context = None,
) -> Dict[str, Any]:
    """PERMANENT: deletes the expense in SuperFaktura. Confirm with the user first.

    Args:
        expense_id: ID of the expense to delete

    Returns:
        Deletion response
    """
    return _get_client(context).get(f"expenses/delete/{expense_id}")


def _apply_read_only() -> None:
    """SUPERFAKTURA_READ_ONLY=1 leaves the write tools out. Decided when the server starts
    (after .env is loaded), never at import, so importing server.py always gives every tool."""
    if os.getenv("SUPERFAKTURA_READ_ONLY", "").strip().lower() in ("1", "true", "yes"):
        for name in WRITE_TOOLS:
            mcp.remove_tool(name)


def main():
    import sys

    from dotenv import load_dotenv

    if "--http" in sys.argv:
        # 0.1.0 has no HTTP mode: an HTTP server would act with the owner's account for anyone
        # who can reach it. Per-user credentials over HTTP need auth first (see the issues).
        print("superfaktura-mcp runs over stdio only; --http is not supported in 0.1.0.", file=sys.stderr)
        sys.exit(2)
    load_dotenv()  # a .env next to the server, for local runs only (never at import)
    _apply_read_only()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
