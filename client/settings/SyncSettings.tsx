import * as React from "react";
import { useEffect, useState } from "react";
import { Formik, Form, Field } from "formik";

import type { QBOAccount, QBOTaxCode, QBOVendor, Settings } from "../types";
import { AccountSelect, VendorSelect, TaxCodeSelect } from "./Inputs";
import getDefaultSettings from "./getDefaultSettings";

const saveSettings = (settings: Settings) => {
  fetch("/settings", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(settings),
  });
};

const SyncSettings = () => {
  const [accounts, setAccounts] = useState<QBOAccount[]>([]);
  const [vendors, setVendors] = useState<QBOVendor[]>([]);
  const [taxCodes, setTaxCodes] = useState<QBOTaxCode[]>([]);
  const [settings, setSettings] = useState<Settings>({});
  const [loading, setLoading] = useState<boolean>(true);

  const loadAccount = async () => {
    const response = await fetch("/qbo/accounts");
    const data = await response.json();
    setAccounts(data);
  };

  const loadVendors = async () => {
    const response = await fetch("/qbo/vendors");
    const data = await response.json();
    setVendors(data);
  };

  const loadTaxCodes = async () => {
    const response = await fetch("/qbo/taxcodes");
    const data = await response.json();
    setTaxCodes(data);
  };

  const loadSettings = async () => {
    const response = await fetch("/settings");
    const data = await response.json();
    if (data) {
      setSettings(data);
    }
  };

  useEffect(() => {
    Promise.all([
      loadAccount(),
      loadVendors(),
      loadTaxCodes(),
      loadSettings(),
    ]).then(() => setLoading(false));
  }, []);

  const defaultSettings = getDefaultSettings({ accounts, vendors, taxCodes });

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      <h3>Settings</h3>
      <Formik
        initialValues={{
          ...defaultSettings,
          ...settings,
        }}
        onSubmit={(values: Settings, { setSubmitting }) => {
          saveSettings(values);
          setSubmitting(false);
        }}
        enableReinitialize
      >
        <Form>
          <AccountSelect
            label="Stripe Clearing Account"
            name="stripeClearingAccountId"
            accounts={accounts}
            accountType="Bank"
          />
          <AccountSelect
            label="Stripe Payout Account"
            name="stripePayoutAccountId"
            accounts={accounts}
            accountType="Bank"
          />
          <VendorSelect
            label="Stripe Vendor"
            name="stripeVendorId"
            vendors={vendors}
          />
          <AccountSelect
            label="Stripe Expense Account"
            name="stripeFeeAccountId"
            accounts={accounts}
            accountType="Expense"
          />
          <AccountSelect
            label="Default Income Account"
            name="defaultIncomeAccountId"
            accounts={accounts}
            accountType="Income"
          />
          <h4>Tax Codes</h4>
          <TaxCodeSelect
            label="Default Tax Code"
            name="defaultTaxCodeId"
            taxCodes={taxCodes}
          />
          <TaxCodeSelect
            label="Exempt Tax Code"
            name="exemptTaxCodeId"
            taxCodes={taxCodes}
          />
          <button type="submit">Save</button>
        </Form>
      </Formik>
    </div>
  );
};

export default SyncSettings;
