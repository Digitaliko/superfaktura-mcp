#!/usr/bin/env python3

import os
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP(name="superfaktura")

BASE_URLS = {
    "sk": "https://moja.superfaktura.sk",
    "cz": "https://moje.superfaktura.cz",
    "at": "https://meine.superfaktura.at",
    "sandbox-sk": "https://sandbox.superfaktura.sk",
    "sandbox-cz": "https://sandbox.superfaktura.cz",
}


class SuperFakturaClient:
    """Client for interacting with SuperFaktura API."""

    def __init__(self):
        self.email = os.getenv("SUPERFAKTURA_EMAIL")
        self.api_key = os.getenv("SUPERFAKTURA_API_KEY")

        if not self.email or not self.api_key:
            raise ValueError("SUPERFAKTURA_EMAIL and SUPERFAKTURA_API_KEY must be set")

        # Support custom API URL (useful for sandbox) or use country-based URL
        self.base_url = os.getenv("SUPERFAKTURA_API_URL")
        if not self.base_url:
            country = os.getenv("SUPERFAKTURA_COUNTRY", "sk")
            self.base_url = BASE_URLS.get(country)
            if not self.base_url:
                raise ValueError(f"Invalid country code: {country}")

    def _get_headers(self) -> Dict[str, str]:
        """Generate authentication headers."""
        return {
            "Authorization": f"SFAPI email={self.email}&apikey={self.api_key}",
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


client = SuperFakturaClient()


@mcp.tool()
def create_invoice(
    client_id: int,
    name: str,
    invoice_items: List[Dict[str, Any]],
    issued_date: Optional[str] = None,
    due_date: Optional[str] = None,
    variable_symbol: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new invoice in SuperFaktura.

    Args:
        client_id: ID of the client to invoice
        name: Invoice name/description
        invoice_items: List of items, each with keys: name, description, unit_price, quantity, tax
        issued_date: Issue date (YYYY-MM-DD), defaults to today
        due_date: Due date (YYYY-MM-DD), defaults to issued_date
        variable_symbol: Variable symbol for payment identification

    Returns:
        Invoice creation response with invoice ID and details
    """
    if not issued_date:
        issued_date = datetime.now().strftime("%Y-%m-%d")
    if not due_date:
        due_date = issued_date

    invoice_data = {
        "Invoice": {
            "client_id": client_id,
            "name": name,
            "issued": issued_date,
            "due": due_date,
            "variable": variable_symbol,
        },
        "InvoiceItem": invoice_items,
    }

    return client.post("invoices/create", invoice_data)


@mcp.tool()
def list_invoices(
    page: int = 1,
    per_page: int = 50,
    status: Optional[str] = None,
    client_id: Optional[int] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List invoices with optional filtering.

    Args:
        page: Page number for pagination
        per_page: Number of results per page (max 100)
        status: Filter by status (1=draft, 2=sent, 3=paid, 99=cancelled)
        client_id: Filter by client ID
        from_date: Filter from date (YYYY-MM-DD)
        to_date: Filter to date (YYYY-MM-DD)

    Returns:
        List of invoices with pagination info
    """
    params = [f"page:{page}", f"per_page:{per_page}"]

    if status:
        params.append(f"status:{status}")
    if client_id:
        params.append(f"client_id:{client_id}")
    if from_date:
        params.append(f"created_since:{from_date}")
    if to_date:
        params.append(f"created_to:{to_date}")

    endpoint = f"invoices/index.json/{'/'.join(params)}"
    return client.get(endpoint)


@mcp.tool()
def get_invoice(invoice_id: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific invoice.

    Args:
        invoice_id: ID of the invoice to retrieve

    Returns:
        Invoice details including items, client info, and payment status
    """
    return client.get(f"invoices/view/{invoice_id}.json")


@mcp.tool()
def send_invoice(invoice_id: int, email: Optional[str] = None) -> Dict[str, Any]:
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

    return client.post("invoices/send", data)


@mcp.tool()
def mark_invoice_paid(
    invoice_id: int, amount: float, payment_date: Optional[str] = None
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

    return client.post("invoice_payments/add", payment_data)


@mcp.tool()
def create_client(
    name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    address: Optional[str] = None,
    city: Optional[str] = None,
    zip_code: Optional[str] = None,
    country: Optional[str] = None,
    ico: Optional[str] = None,
    dic: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new client in SuperFaktura.

    Args:
        name: Client/company name
        email: Client email address
        phone: Client phone number
        address: Street address
        city: City
        zip_code: ZIP/postal code
        country: Country
        ico: Company registration number (IČO)
        dic: Tax ID number (DIČ)

    Returns:
        Client creation response with client ID
    """
    client_data = {"Client": {"name": name}}

    if email:
        client_data["Client"]["email"] = email
    if phone:
        client_data["Client"]["phone"] = phone
    if address:
        client_data["Client"]["address"] = address
    if city:
        client_data["Client"]["city"] = city
    if zip_code:
        client_data["Client"]["zip"] = zip_code
    if country:
        client_data["Client"]["country"] = country
    if ico:
        client_data["Client"]["ico"] = ico
    if dic:
        client_data["Client"]["dic"] = dic

    return client.post("clients/create", client_data)


@mcp.tool()
def list_clients(page: int = 1, per_page: int = 50) -> Dict[str, Any]:
    """
    List all clients with pagination.

    Args:
        page: Page number for pagination
        per_page: Number of results per page (max 100)

    Returns:
        List of clients with pagination info
    """
    endpoint = f"clients/index.json/page:{page}/per_page:{per_page}/listinfo:1"
    return client.get(endpoint)


@mcp.tool()
def get_client(client_id: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific client.

    Args:
        client_id: ID of the client to retrieve

    Returns:
        Client details including contact information and invoice history
    """
    return client.get(f"clients/view/{client_id}.json")


@mcp.tool()
def update_client(client_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update client information.

    Args:
        client_id: ID of the client to update
        updates: Dictionary of fields to update (name, email, phone, address, etc.)

    Returns:
        Update response
    """
    client_data = {"Client": {"id": client_id, **updates}}
    return client.patch(f"clients/edit/{client_id}", client_data)


@mcp.tool()
def create_expense(
    name: str,
    amount: float,
    expense_date: Optional[str] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
    variable_symbol: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new expense record.

    Args:
        name: Expense name/description
        amount: Expense amount
        expense_date: Expense date (YYYY-MM-DD), defaults to today
        category: Expense category
        description: Additional description
        variable_symbol: Variable symbol for tracking

    Returns:
        Expense creation response with expense ID
    """
    if not expense_date:
        expense_date = datetime.now().strftime("%Y-%m-%d")

    expense_data = {
        "Expense": {
            "name": name,
            "amount": amount,
            "date": expense_date,
        }
    }

    if category:
        expense_data["Expense"]["category"] = category
    if description:
        expense_data["Expense"]["description"] = description
    if variable_symbol:
        expense_data["Expense"]["variable"] = variable_symbol

    return client.post("expenses/add", expense_data)


@mcp.tool()
def list_expenses(
    page: int = 1,
    per_page: int = 50,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List expenses with optional date filtering.

    Args:
        page: Page number for pagination
        per_page: Number of results per page (max 100)
        from_date: Filter from date (YYYY-MM-DD)
        to_date: Filter to date (YYYY-MM-DD)

    Returns:
        List of expenses with pagination info
    """
    params = [f"page:{page}", f"per_page:{per_page}"]

    if from_date:
        params.append(f"date_from:{from_date}")
    if to_date:
        params.append(f"date_to:{to_date}")

    endpoint = f"expenses/index.json/{'/'.join(params)}"
    return client.get(endpoint)


@mcp.tool()
def get_expense(expense_id: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific expense.

    Args:
        expense_id: ID of the expense to retrieve

    Returns:
        Expense details
    """
    return client.get(f"expenses/view/{expense_id}.json")


if __name__ == "__main__":
    mcp.run(transport="stdio")
