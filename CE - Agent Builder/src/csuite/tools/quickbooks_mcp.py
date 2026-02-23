"""
QuickBooks MCP Server for CFO Agent.

This is a custom MCP server that provides access to QuickBooks Online data
for financial analysis. It wraps the QuickBooks API and exposes relevant
financial data as MCP tools.

Note: This is a stub implementation. Full implementation requires:
1. QuickBooks developer account and app credentials
2. OAuth 2.0 authentication flow
3. API client implementation

For production use, see: https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import httpx

from csuite.config import get_settings


@dataclass
class QuickBooksConfig:
    """Configuration for QuickBooks API access."""

    client_id: str
    client_secret: str
    refresh_token: str
    realm_id: str
    base_url: str = "https://quickbooks.api.intuit.com"


class QuickBooksMCP:
    """QuickBooks MCP Server for financial data access.

    Provides tools for:
    - Profit & Loss reports
    - Balance Sheet reports
    - Accounts Receivable aging
    - Cash flow statements
    - Project/Customer profitability
    """

    def __init__(self, config: QuickBooksConfig | None = None):
        settings = get_settings()

        if config:
            self.config = config
        elif all([
            settings.quickbooks_client_id,
            settings.quickbooks_client_secret,
            settings.quickbooks_refresh_token,
            settings.quickbooks_realm_id,
        ]):
            self.config = QuickBooksConfig(
                client_id=settings.quickbooks_client_id,
                client_secret=settings.quickbooks_client_secret,
                refresh_token=settings.quickbooks_refresh_token,
                realm_id=settings.quickbooks_realm_id,
            )
        else:
            self.config = None

        self._access_token: str | None = None
        self._token_expires: datetime | None = None

    @property
    def is_configured(self) -> bool:
        """Check if QuickBooks credentials are configured."""
        return self.config is not None

    async def _refresh_access_token(self) -> str:
        """Refresh the OAuth access token."""
        if not self.config:
            raise ValueError("QuickBooks not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.config.refresh_token,
                },
                auth=(self.config.client_id, self.config.client_secret),
            )
            response.raise_for_status()
            data = response.json()

            self._access_token = data["access_token"]
            # Token typically expires in 1 hour
            self._token_expires = datetime.now()

            return self._access_token

    async def _get_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        if self._access_token and self._token_expires:
            # Refresh if within 5 minutes of expiry
            if (self._token_expires - datetime.now()).total_seconds() > 300:
                return self._access_token

        return await self._refresh_access_token()

    async def _api_request(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        """Make an authenticated API request."""
        if not self.config:
            raise ValueError("QuickBooks not configured")

        token = await self._get_token()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.config.base_url}/v3/company/{self.config.realm_id}/{endpoint}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
                params=params,
            )
            response.raise_for_status()
            return response.json()

    # =========================================================================
    # MCP Tool Implementations
    # =========================================================================

    async def get_profit_and_loss(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Get Profit & Loss report.

        Args:
            start_date: Report start date (default: start of current year)
            end_date: Report end date (default: today)

        Returns:
            P&L report data including revenue, expenses, and net income
        """
        params = {}
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()

        return await self._api_request("reports/ProfitAndLoss", params)

    async def get_balance_sheet(
        self,
        as_of_date: date | None = None,
    ) -> dict[str, Any]:
        """Get Balance Sheet report.

        Args:
            as_of_date: Report date (default: today)

        Returns:
            Balance sheet data including assets, liabilities, and equity
        """
        params = {}
        if as_of_date:
            params["as_of_date"] = as_of_date.isoformat()

        return await self._api_request("reports/BalanceSheet", params)

    async def get_ar_aging(self) -> dict[str, Any]:
        """Get Accounts Receivable Aging report.

        Returns:
            AR aging data showing outstanding invoices by age bucket
        """
        return await self._api_request("reports/AgedReceivables")

    async def get_cash_flow(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Get Cash Flow Statement.

        Args:
            start_date: Report start date
            end_date: Report end date

        Returns:
            Cash flow data including operating, investing, financing activities
        """
        params = {}
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()

        return await self._api_request("reports/CashFlow", params)

    async def get_customer_profitability(
        self,
        customer_id: str | None = None,
    ) -> dict[str, Any]:
        """Get profitability by customer/project.

        Args:
            customer_id: Specific customer ID, or None for all customers

        Returns:
            Revenue and profit data by customer
        """
        params = {}
        if customer_id:
            params["customer"] = customer_id

        return await self._api_request("reports/CustomerIncome", params)

    async def get_invoice_list(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Get list of invoices.

        Args:
            start_date: Filter invoices from this date
            end_date: Filter invoices to this date

        Returns:
            List of invoices with status, amounts, and customer info
        """
        query = "SELECT * FROM Invoice"
        conditions = []

        if start_date:
            conditions.append(f"TxnDate >= '{start_date.isoformat()}'")
        if end_date:
            conditions.append(f"TxnDate <= '{end_date.isoformat()}'")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        return await self._api_request("query", {"query": query})

    # =========================================================================
    # MCP Server Definition
    # =========================================================================

    def get_mcp_tools(self) -> list[dict[str, Any]]:
        """Get MCP tool definitions for this server.

        Returns list of tool definitions that can be registered with Claude.
        """
        return [
            {
                "name": "quickbooks_profit_and_loss",
                "description": "Get Profit & Loss report from QuickBooks",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date (YYYY-MM-DD)",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date (YYYY-MM-DD)",
                        },
                    },
                },
            },
            {
                "name": "quickbooks_balance_sheet",
                "description": "Get Balance Sheet report from QuickBooks",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "as_of_date": {
                            "type": "string",
                            "description": "As of date (YYYY-MM-DD)",
                        },
                    },
                },
            },
            {
                "name": "quickbooks_ar_aging",
                "description": "Get Accounts Receivable Aging report from QuickBooks",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "quickbooks_cash_flow",
                "description": "Get Cash Flow Statement from QuickBooks",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date (YYYY-MM-DD)",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date (YYYY-MM-DD)",
                        },
                    },
                },
            },
            {
                "name": "quickbooks_customer_profitability",
                "description": "Get customer/project profitability from QuickBooks",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Customer ID (optional, omit for all)",
                        },
                    },
                },
            },
        ]
