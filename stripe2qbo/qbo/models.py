from typing import List, Optional, Literal

from pydantic import BaseModel


class CompanyInfo(BaseModel):
    CompanyName: str
    Country: str


class CurrencyRef(BaseModel):
    value: str
    name: Optional[str]


class ItemRef(BaseModel):
    value: str
    name: Optional[str]


class TaxRateRef(BaseModel):
    value: str
    name: Optional[str]


class TaxCodeRef(BaseModel):
    value: str


class Customer(BaseModel):
    DisplayName: str
    Id: str
    CurrencyRef: CurrencyRef


class TaxRateDetail(BaseModel):
    TaxRateRef: TaxRateRef


class TaxRateList(BaseModel):
    TaxRateDetail: List[TaxRateDetail]


class TaxCode(BaseModel):
    Id: str
    SalesTaxRateList: TaxRateList


class TaxLineDetail(BaseModel):
    TaxRateRef: TaxRateRef
    PercentBased: bool = True
    TaxPercent: float
    NetAmountTaxable: float


class TaxLineModel(BaseModel):
    DetailType: Literal["TaxLineDetail"] = "TaxLineDetail"
    Amount: float
    TaxLineDetail: TaxLineDetail


class TaxDetail(BaseModel):
    TotalTax: float
    TaxLine: Optional[List[TaxLineModel]] = None
    TxnTaxCodeRef: Optional[TaxCodeRef] = None


class SalesItemLineDetail(BaseModel):
    ItemRef: ItemRef
    TaxCodeRef: Optional[TaxCodeRef]


class InvoiceLine(BaseModel):
    Amount: float
    Description: str
    SalesItemLineDetail: SalesItemLineDetail
    DetailType: Literal["SalesItemLineDetail"] = "SalesItemLineDetail"