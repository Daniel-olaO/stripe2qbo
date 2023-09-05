from datetime import datetime
from typing import Any, Optional, Mapping, List
from requests import Response

from stripe2qbo.qbo.auth import Token
from stripe2qbo.qbo.models import (
    Customer,
    InvoiceLine,
    ItemRef,
    QBOCurrency,
    TaxCode,
    TaxDetail,
)
from stripe2qbo.qbo.qbo_request import qbo_request


class QBO:
    realm_id: str | None = None
    access_token: str | None = None

    def set_token(self, token: Token) -> None:
        self.realm_id = token.realm_id
        self.access_token = token.access_token

    def _request(
        self, path: str, method: str = "GET", body: Optional[Mapping[str, Any]] = None
    ) -> Response:
        if self.access_token is None or self.realm_id is None:
            raise Exception("QBO token not set")

        response = qbo_request(
            path=path,
            method=method,
            body=body,
            access_token=self.access_token,
            realm_id=self.realm_id,
        )
        return response

    def _query(self, query: str) -> Response:
        response = self._request(f"/query?query={query}")
        if "QueryResponse" not in response.json():
            raise Exception(f"Query failed: {response.json()}")
        return response

    def get_tax_code(self, tax_code_id: str) -> Optional[TaxCode]:
        response = self._query(f"select * from TaxCode where Id = '{tax_code_id}'")
        tax_codes = response.json()["QueryResponse"].get("TaxCode", [])
        if len(tax_codes) == 0:
            return None
        else:
            return TaxCode(**tax_codes[0])

    def get_customer_by_name(self, customer_name: str) -> Optional[Customer]:
        response = self._query(
            f"select * from Customer where DisplayName = '{customer_name}'"
        )
        customers = response.json()["QueryResponse"].get("Customer", [])
        if len(customers) == 0:
            return None
        else:
            return customers[0]

    def create_customer(self, customer_name: str, currency: str) -> Customer:
        response = self._request(
            path="customer",
            method="POST",
            body={
                "DisplayName": customer_name,
                "CurrencyRef": {
                    "value": currency,
                },
            },
        )
        if "Customer" not in response.json():
            raise Exception(f"Error creating customer: {response.json()}")
        return Customer(**response.json()["Customer"])

    def get_or_create_customer(self, customer_name: str, currency: str) -> Customer:
        customer = self.get_customer_by_name(customer_name)
        if customer is None:
            customer = self.create_customer(customer_name, currency)

            if customer.CurrencyRef.value != currency:
                # if already exists with different currency, create a new one
                return self.create_customer(f"{customer_name} ({currency})", currency)

        return customer

    def get_item_by_name(self, item_name: str) -> Optional[ItemRef]:
        response = self._query(f"select * from Item where Name = '{item_name}'")
        items = response.json()["QueryResponse"].get("Item", [])
        if len(items) == 0:
            return None

        return ItemRef(
            value=items[0]["Id"],
            name=items[0]["Name"],
        )

    def create_item(self, item_name: str, account_id: str) -> ItemRef:
        response = self._request(
            path="item",
            method="POST",
            body={
                "Name": item_name,
                "Type": "Service",
                "IncomeAccountRef": {
                    "value": account_id,
                },
            },
        )

        return ItemRef(
            value=response.json()["Item"]["Id"],
            name=response.json()["Item"]["Name"],
        )

    def get_or_create_item(self, item_name: str, account_id: str) -> ItemRef:
        item = self.get_item_by_name(item_name)
        if item is None:
            item = self.create_item(item_name, account_id)
        return item

    def create_account(self, account_name: str, account_type: str) -> str:
        body = {
            "Name": account_name,
            "AccountType": account_type,
        }
        response = self._request(path="/account", body=body, method="POST")
        return response.json()["Account"]["Id"]

    def get_account_id(self, account_name: str) -> Optional[str]:
        response = self._query(f"select * from Account where Name = '{account_name}'")
        accounts = response.json()["QueryResponse"].get("Account", [])

        if len(accounts) == 0:
            return None

        if len(accounts) > 1:
            raise Exception(f"Multiple accounts found with {account_name}")

        return accounts[0]["Id"]

    def get_or_create_account(self, account_name: str, account_type: str) -> str:
        acount_id = self.get_account_id(account_name)
        if acount_id is not None:
            return acount_id
        return self.create_account(account_name, account_type)

    def create_invoice(
        self,
        customer_id: str,
        lines: List[InvoiceLine],
        created_date: Optional[datetime],
        currency: Optional[QBOCurrency] = "USD",
        private_note: Optional[str] = None,
        due_date: Optional[datetime] = None,
        txn_date: Optional[datetime] = None,
        tax_detail: Optional[TaxDetail] = None,
        inv_number: Optional[str] = None,
    ) -> str:

        body = {
            "CustomerRef": {
                "value": customer_id,
            },
            "CurrencyRef": {
                "value": currency,
            },
            "Line": [line.model_dump() for line in lines],
            "TxnDate": txn_date.strftime("%Y-%m-%d") if txn_date else None,
            "DueDate": due_date.strftime("%Y-%m-%d") if due_date else None,
            "TxnTaxDetail": tax_detail.model_dump() if tax_detail else None,
            "PrivateNote": private_note,
            "DocNumber": inv_number,
        }

        if due_date:
            body["DueDate"] = due_date.strftime("%Y-%m-%d")
        if created_date:
            body["TxnDate"] = created_date.strftime("%Y-%m-%d")

        response = self._request(
            path="invoice",
            method="POST",
            body=body,
        )
        return response.json()["Invoice"]["Id"]

    def create_invoice_payment(
        self,
        invoice_id: Optional[str],
        customer_id: str,
        amount: float,
        date: datetime,
        qbo_account_id: str,
        currency: QBOCurrency,
        exchange_rate: Optional[float],
        private_note: str = "",
    ) -> str:
        # TODO: Payment method?

        body = {
            "TotalAmt": amount,
            "CustomerRef": {"value": customer_id},
            "TxnDate": date.strftime("%Y-%m-%d"),
            "DepositToAccountRef": {"value": qbo_account_id},
            "PrivateNote": private_note,
            "CurrencyRef": {"value": currency},
            "ExchangeRate": exchange_rate or "1",
        }

        if invoice_id:
            body["Line"] = [
                {
                    "Amount": amount,
                    "LinkedTxn": [{"TxnId": invoice_id, "TxnType": "Invoice"}],
                }
            ]
        response = self._request(path="/payment", body=body, method="POST")

        return response.json()["Payment"]["Id"]

    def create_expense(
        self,
        amount: float,
        date: datetime,
        bank_account_id: str,
        vendor_id: str,
        expense_account_id: str,
        private_note: str = "",
        description: Optional[str] = None,
    ) -> str:
        body = {
            "TotalAmt": amount,
            "AccountRef": {"value": bank_account_id},
            "PaymentType": "Check",
            "Line": [
                {
                    "Amount": amount,
                    "DetailType": "AccountBasedExpenseLineDetail",
                    "AccountBasedExpenseLineDetail": {
                        "AccountRef": {"value": expense_account_id},
                    },
                    "Description": description,
                }
            ],
            "EntityRef": {"value": vendor_id},
            "TxnDate": date.strftime("%Y-%m-%d"),
            "PrivateNote": private_note,
        }

        response = self._request(path="/purchase", body=body, method="POST")
        return response.json()["Purchase"]["Id"]

    def create_transfer(
        self,
        amount: float,
        date: datetime,
        source_account_id: str,
        destination_account_id: str,
        private_note: str = "",
    ) -> str:
        body = {
            "Amount": amount,
            "FromAccountRef": {"value": source_account_id},
            "ToAccountRef": {"value": destination_account_id},
            "TxnDate": date.strftime("%Y-%m-%d"),
            "PrivateNote": private_note,
        }

        response = self._request(path="/transfer", body=body, method="POST")
        return response.json()["Transfer"]["Id"]