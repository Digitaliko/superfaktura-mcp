#!/usr/bin/env python3

import os
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastmcp import FastMCP, Context
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP(name="superfaktura")


def get_credentials_from_context(context: Context = None) -> tuple:
    """
    Extract SuperFaktura credentials from MCP request context/headers.

    For public MCP deployments, users configure credentials in their
    Claude Desktop config as custom headers:

    {
      "mcpServers": {
        "superfaktura": {
          "url": "https://your-mcp-server.com/mcp",
          "headers": {
            "X-SuperFaktura-Email": "user@example.com",
            "X-SuperFaktura-API-Key": "user-key",
            "X-SuperFaktura-Country": "sk",
            "X-SuperFaktura-Company-ID": "optional"
          }
        }
      }
    }

    Returns:
        tuple: (email, apikey, company_id, country)
    """
    if not context:
        # Fallback to environment variables
        return (
            os.getenv("SUPERFAKTURA_EMAIL"),
            os.getenv("SUPERFAKTURA_API_KEY"),
            os.getenv("SUPERFAKTURA_COMPANY_ID"),
            os.getenv("SUPERFAKTURA_COUNTRY", "sk"),
        )

    # Try to get credentials from request headers (for HTTP/SSE transport)
    headers = getattr(context, "headers", {}) or {}

    email = headers.get("x-superfaktura-email") or os.getenv("SUPERFAKTURA_EMAIL")
    apikey = headers.get("x-superfaktura-api-key") or os.getenv("SUPERFAKTURA_API_KEY")
    company_id = headers.get("x-superfaktura-company-id") or os.getenv("SUPERFAKTURA_COMPANY_ID")
    country = headers.get("x-superfaktura-country") or os.getenv("SUPERFAKTURA_COUNTRY", "sk")

    return email, apikey, company_id, country

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
    and per-request credentials (for multi-tenant deployments).
    """

    def __init__(
        self,
        email: Optional[str] = None,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        country: str = "sk",
        company_id: Optional[str] = None,
        module: str = "superfaktura-mcp/2.0",
    ):
        """
        Initialize SuperFaktura API client.

        Args:
            email: Account email (falls back to SUPERFAKTURA_EMAIL env var)
            api_key: API key (falls back to SUPERFAKTURA_API_KEY env var)
            api_url: Custom API URL (falls back to SUPERFAKTURA_API_URL env var)
            country: Country code - sk, cz, at, sandbox-sk, sandbox-cz (default: sk)
            company_id: Company ID (optional, falls back to SUPERFAKTURA_COMPANY_ID env var)
            module: Module identifier for API (default: superfaktura-mcp/2.0)

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
            resolved_country = country or os.getenv("SUPERFAKTURA_COUNTRY", "sk")
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

    def _request(
        self, method: str, endpoint: str, data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to SuperFaktura API."""
        url = f"{self.base_url}/{endpoint}"
        headers = self._get_headers()

        try:
            response = requests.request(
                method=method, url=url, json=data, headers=headers, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "failed"}

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


# Global client for single-tenant deployments using environment variables
# For multi-tenant: create client instances with SuperFakturaClient(email, api_key)
try:
    client = SuperFakturaClient()
except ValueError:
    # No env vars set - multi-tenant mode, credentials must be provided per-request
    client = None  # type: ignore


def _get_client(context: Context = None) -> SuperFakturaClient:
    """
    Get SuperFaktura client with credentials from context or environment.

    For public MCP deployments, credentials come from custom headers in
    Claude Desktop config. For local/single-tenant, uses environment variables.

    Args:
        context: FastMCP context containing request headers

    Returns:
        Configured SuperFakturaClient instance

    Raises:
        ValueError: If no credentials available
    """
    email, apikey, company_id, country = get_credentials_from_context(context)

    if not email or not apikey:
        raise ValueError(
            "SuperFaktura credentials not found. "
            "Configure credentials in Claude Desktop config headers "
            "(X-SuperFaktura-Email, X-SuperFaktura-API-Key) "
            "or set SUPERFAKTURA_EMAIL and SUPERFAKTURA_API_KEY environment variables."
        )

    return SuperFakturaClient(
        email=email,
        api_key=apikey,
        company_id=company_id,
        country=country,
    )


@mcp.tool()
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
        invoice_items: List of items, each with keys: name, description, unit_price, quantity, tax (and optional AccountingDetail)
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


@mcp.tool()
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

context: Context = None,
) -> Dict[str, Any]:
    """
    List invoices with comprehensive filtering and sorting.

    Args:
        page: Page number for pagination
        per_page: Number of results per page (max 200)
        listinfo: Show meta data about result (0=no, 1=yes)
        direction: Sorting direction (ASC or DESC)
        sort: Attribute to sort by (e.g., 'regular_count', 'created', 'amount')
        type: Document type filter (proforma, regular, etc.). Use | for multiple (e.g., 'regular|proforma')
        status: Filter by status (1=draft, 2=sent, 3=paid, 99=cancelled). Use | for multiple
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
        search: Base64 encoded search string
        tag: Filter by tag ID
        ignore: Invoice IDs to exclude. Use | for multiple (e.g., '1|2|3')

    Returns:
        List of invoices with pagination info and metadata
    """
    # Validate per_page max
    if per_page > 200:
        per_page = 200

    params = [
        f"page:{page}",
        f"per_page:{per_page}",
        f"listinfo:{listinfo}",
        f"direction:{direction}",
        f"sort:{sort}",
    ]

    if type:
        params.append(f"type:{type}")
    if status:
        params.append(f"status:{status}")
    if client_id:
        params.append(f"client_id:{client_id}")

    # Time-based filters
    if created_since or created_to:
        params.append("created:3")
        if created_since:
            params.append(f"created_since:{created_since}")
        if created_to:
            params.append(f"created_to:{created_to}")

    if modified_since or modified_to:
        params.append("modified:3")
        if modified_since:
            params.append(f"modified_since:{modified_since}")
        if modified_to:
            params.append(f"modified_to:{modified_to}")

    if delivery_since or delivery_to:
        params.append("delivery:3")
        if delivery_since:
            params.append(f"delivery_since:{delivery_since}")
        if delivery_to:
            params.append(f"delivery_to:{delivery_to}")

    if paydate_since or paydate_to:
        params.append("paydate:3")
        if paydate_since:
            params.append(f"paydate_since:{paydate_since}")
        if paydate_to:
            params.append(f"paydate_to:{paydate_to}")

    # Amount filters
    if amount_from is not None:
        params.append(f"amount_from:{amount_from}")
    if amount_to is not None:
        params.append(f"amount_to:{amount_to}")

    # Other filters
    if payment_type:
        params.append(f"payment_type:{payment_type}")
    if delivery_type:
        params.append(f"delivery_type:{delivery_type}")
    if invoice_no_formatted:
        params.append(f"invoice_no_formatted:{invoice_no_formatted}")
    if order_no:
        params.append(f"order_no:{order_no}")
    if variable:
        params.append(f"variable:{variable}")
    if search:
        params.append(f"search:{search}")
    if tag:
        params.append(f"tag:{tag}")
    if ignore:
        params.append(f"ignore:{ignore}")

    endpoint = f"invoices/index.json/{'/'.join(params)}"
    return _get_client(context).get(endpoint)


@mcp.tool()
def get_invoice(invoice_id: int,
context: Context = None,
) -> Dict[str, Any]:
    """
    Get detailed information about a specific invoice.

    Args:
        invoice_id: ID of the invoice to retrieve

    Returns:
        Invoice details including items, client info, and payment status
    """
    return _get_client(context).get(f"invoices/view/{invoice_id}.json")


@mcp.tool()
def send_invoice(invoice_id: int, email: Optional[str] = None,
context: Context = None,
) -> Dict[str, Any]:
    """
    Send an invoice via email.

    Args:
        invoice_id: ID of the invoice to send
        email: Optional override email address (uses client email by default)

    Returns:
        Response indicating if email was sent successfully
    """
    data = {"Invoice": {"id": invoice_id}}
    if email:
        data["Invoice"]["email"] = email

    return _get_client(context).post("invoices/send", data)


@mcp.tool()
def mark_invoice_paid(
    invoice_id: int, amount: float, payment_date: Optional[str] = None,
    context: Context = None,
) -> Dict[str, Any]:
    """
    Mark an invoice as paid by recording a payment.

    Args:
        invoice_id: ID of the invoice
        amount: Payment amount
        payment_date: Payment date (YYYY-MM-DD), defaults to today

    Returns:
        Payment recording response
    """
    if not payment_date:
        payment_date = datetime.now().strftime("%Y-%m-%d")

    payment_data = {
        "InvoicePayment": {
            "invoice_id": invoice_id,
            "amount": amount,
            "payment_type": "transfer",
            "created": payment_date,
        }
    }

    return _get_client(context).post("invoice_payments/add", payment_data)


@mcp.tool()
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


@mcp.tool()
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

context: Context = None,
) -> Dict[str, Any]:
    """
    List all clients with comprehensive filtering and sorting.

    Args:
        page: Page number for pagination
        per_page: Number of results per page
        listinfo: Show meta data about result (0=no, 1=yes)
        direction: Sorting direction (ASC or DESC)
        sort: Attribute to sort by
        char_filter: Filter by first letter of client name (use # for non-letters)
        search: Base64 encoded search string (searches name, ICO, DIC, IC_DPH, bank_account, email, address, city, zip, state, country, phone, fax, comment, tags, UUID)
        search_uuid: Search by exact UUID
        tag: Filter by tag ID
        created_since: Creation date from (YYYY-MM-DD, requires created:3)
        created_to: Creation date to (YYYY-MM-DD, requires created:3)
        modified_since: Last modification date from (YYYY-MM-DD, requires modified:3)
        modified_to: Last modification date to (YYYY-MM-DD, requires modified:3)

    Returns:
        List of clients with pagination info and metadata
    """
    params = [
        f"page:{page}",
        f"per_page:{per_page}",
        f"listinfo:{listinfo}",
        f"direction:{direction}",
        f"sort:{sort}",
    ]

    if char_filter:
        params.append(f"char_filter:{char_filter}")
    if search:
        params.append(f"search:{search}")
    if search_uuid:
        params.append(f"search_uuid:{search_uuid}")
    if tag:
        params.append(f"tag:{tag}")

    # Time-based filters
    if created_since or created_to:
        params.append("created:3")
        if created_since:
            params.append(f"created_since:{created_since}")
        if created_to:
            params.append(f"created_to:{created_to}")

    if modified_since or modified_to:
        params.append("modified:3")
        if modified_since:
            params.append(f"modified_since:{modified_since}")
        if modified_to:
            params.append(f"modified_to:{modified_to}")

    endpoint = f"clients/index.json/{'/'.join(params)}"
    return _get_client(context).get(endpoint)


@mcp.tool()
def get_client(client_id: int, context: Context = None,
) -> Dict[str, Any]:
    """
    Get detailed information about a specific client.

    Args:
        client_id: ID of the client to retrieve

    Returns:
        Client details including contact information and invoice history
    """
    return _get_client(context).get(f"clients/view/{client_id}.json")


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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

context: Context = None,
) -> Dict[str, Any]:
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
        search: Base64 encoded search string
        status: Expense status filter. Use | for multiple (e.g., '1|2')
        type: Expense type filter

    Returns:
        List of expenses with pagination info and metadata
    """
    # Validate per_page max
    if per_page > 100:
        per_page = 100

    params = [
        f"page:{page}",
        f"per_page:{per_page}",
        f"listinfo:{listinfo}",
        f"direction:{direction}",
        f"sort:{sort}",
    ]

    if amount_from is not None:
        params.append(f"amount_from:{amount_from}")
    if amount_to is not None:
        params.append(f"amount_to:{amount_to}")
    if category:
        params.append(f"category:{category}")
    if client_id:
        params.append(f"client_id:{client_id}")

    # Time-based filters
    if created_since or created_to:
        params.append("created:3")
        if created_since:
            params.append(f"created_since:{created_since}")
        if created_to:
            params.append(f"created_to:{created_to}")

    if modified_since or modified_to:
        params.append("modified:3")
        if modified_since:
            params.append(f"modified_since:{modified_since}")
        if modified_to:
            params.append(f"modified_to:{modified_to}")

    if delivery_since or delivery_to:
        params.append("delivery:3")
        if delivery_since:
            params.append(f"delivery_since:{delivery_since}")
        if delivery_to:
            params.append(f"delivery_to:{delivery_to}")

    if due:
        params.append(f"due:{due}")
    if payment_type:
        params.append(f"payment_type:{payment_type}")
    if search:
        params.append(f"search:{search}")
    if status:
        params.append(f"status:{status}")
    if type:
        params.append(f"type:{type}")

    endpoint = f"expenses/index.json/{'/'.join(params)}"
    return _get_client(context).get(endpoint)


@mcp.tool()
def get_expense(expense_id: int,
context: Context = None,
) -> Dict[str, Any]:
    """
    Get detailed information about a specific expense.

    Args:
        expense_id: ID of the expense to retrieve

    Returns:
        Expense details
    """
    return _get_client(context).get(f"expenses/view/{expense_id}.json")


# ============================================================================
# Additional Invoice Operations
# ============================================================================


@mcp.tool()
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


@mcp.tool()
def get_invoice_pdf(invoice_id: int, language: Optional[str] = None,
context: Context = None,
) -> Dict[str, Any]:
    """
    Get invoice PDF download URL and metadata.

    Args:
        invoice_id: ID of the invoice
        language: Optional language code (eng, slo, cze, deu, etc.)

    Returns:
        Response with PDF URL and metadata
    """
    endpoint = f"invoices/pdf/{invoice_id}"
    if language:
        endpoint += f"/lang:{language}"

    return _get_client(context).get(endpoint)


@mcp.tool()
def delete_invoice(invoice_id: int,
context: Context = None,
) -> Dict[str, Any]:
    """
    Delete an invoice.

    Args:
        invoice_id: ID of the invoice to delete

    Returns:
        Deletion response
    """
    return _get_client(context).delete(f"invoices/delete/{invoice_id}")


@mcp.tool()
def set_invoice_language(invoice_id: int, language: str,
context: Context = None,
) -> Dict[str, Any]:
    """
    Set invoice language.

    Args:
        invoice_id: ID of the invoice
        language: Language code (eng, slo, cze, deu, hun, pol, rom, rus, ukr, hrv)

    Returns:
        Update response
    """
    data = {"InvoiceSetting": {"language": language}}
    return _get_client(context).post(f"invoices/setinvoicelanguage/{invoice_id}", data)


# ============================================================================
# Additional Client Operations
# ============================================================================


@mcp.tool()
def delete_client(client_id: int,
context: Context = None,
) -> Dict[str, Any]:
    """
    Delete a client.

    Args:
        client_id: ID of the client to delete

    Returns:
        Deletion response
    """
    return _get_client(context).delete(f"clients/delete/{client_id}")


# ============================================================================
# Additional Expense Operations
# ============================================================================


@mcp.tool()
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


@mcp.tool()
def delete_expense(expense_id: int,
context: Context = None,
) -> Dict[str, Any]:
    """
    Delete an expense.

    Args:
        expense_id: ID of the expense to delete

    Returns:
        Deletion response
    """
    return _get_client(context).delete(f"expenses/delete/{expense_id}")


if __name__ == "__main__":
    mcp.run(transport="stdio")
