# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Trip(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		advance_given_to_driver: DF.Currency
		advance_jv: DF.Link | None
		amended_from: DF.Link | None
		balance_amount: DF.Currency
		bus_asset: DF.Link | None
		company: DF.Link
		driver: DF.Link
		rental_amount: DF.Currency
		rental_owner: DF.Data | None
		rented_vehicle_number: DF.Data | None
		settlement_jv: DF.Link | None
		settlement_status: DF.Literal["Pending", "Driver Owes Company", "Company Owes Driver", "Settled"]
		total_expense: DF.Currency
		trip_date: DF.Date
		trip_status: DF.Literal["Open", "On Trip", "Completed", "Settled"]
		vehicle_type: DF.Literal["Own Bus", "Rented Bus"]
	# end: auto-generated types

	
	def onload(self):
		if not self.advance_given_to_driver:
			default_adv= frappe.db.get_single_value("Transport Settings","default_driver_advance_amount")
			if default_adv:
				self.advance_given_to_driver= default_adv
		
	def on_submit(self):
		self.create_advance_jv()
	
	def on_cancel(self):
		self.cancel_linked_jv(self.settlement_jv, "settlement_jv")
		self.cancel_linked_jv(self.advance_jv, "advance_jv")
		self.db_set("trip_status", "Open")
		self.db_set("settlement_status", "Pending")
		self.db_set("balance_amount", 0)

	def cancel_linked_jv(self, jv_name, fieldname):
		if not jv_name:
			return

		jv_doc = frappe.get_doc("Journal Entry", jv_name)
		if jv_doc.docstatus == 1:
			jv_doc.cancel()

		self.db_set(fieldname, None)

	def create_advance_jv(self):
		if not self.advance_given_to_driver or self.advance_given_to_driver<=0:
			frappe.throw("Please enter advance given to driver")
		driver_name=frappe.db.get_value("Employee",self.driver,"employee_name")
		cash_account=self.get_cash_account()
		driver_advance_acc=self.get_driver_advance_acc()
		jv=frappe.get_doc({
			"doctype":"Journal Entry",
			"voucher_type":"Cash Entry",
			"posting_date": self.trip_date,
            "company": self.company,
            "accounts": [
                {
                    "account": driver_advance_acc,
                    "debit_in_account_currency": self.advance_given_to_driver,
                    "credit_in_account_currency": 0,
                    "party_type": "Employee",
                    "party": self.driver
                },
				{
					"account":cash_account,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": self.advance_given_to_driver
				}
			]
		})
		jv.insert(ignore_permissions=True)
		jv.submit()

		self.db_set("advance_jv",jv.name)
		self.db_set("trip_status","On Trip")

	def get_cash_account(self):
		account=frappe.db.get_value("Account",{
			"account_name":"Cash",
			"company":self.company,
			"is_group":0,
		},"name")
		if not account:
			frappe.throw(f"Cash account is not available")
		return account
	
	def get_driver_advance_acc(self):
		account=frappe.db.get_value("Account",{
			"account_name":"Driver Advances",
			"company":self.company,
			"is_group":0,
		},"name")
		if not account:
			frappe.throw(f"Driver account is not available")
		return account
	
	def on_update_after_submit(self):
		if self.settlement_jv and self.settlement_status!="Settled":
			jv_read=frappe.db.get_value("Journal Entry",self.settlement_jv,"total_debit")
			if jv_read:
				self.balance_amount=0
				self.settlement_status="Settled"
				self.trip_status="Settled"

	def create_settlement_jv(self):
		if self.settlement_jv:
			frappe.throw("Settlement JV is already created for this Trip.")

		if not self.balance_amount or self.balance_amount == 0:
			frappe.throw("Balance amount must be non-zero to create a settlement entry.")

		if self.settlement_status not in ("Company Owes Driver", "Driver Owes Company"):
			frappe.throw("Settlement JV can only be created when a balance is pending.")

		cash_account = self.get_cash_account()
		driver_advance_account = self.get_driver_advance_acc()
		settlement_amount = abs(self.balance_amount)

		if self.balance_amount < 0:
			accounts = [
				{
					"account": cash_account,
					"debit_in_account_currency": settlement_amount,
					"credit_in_account_currency": 0,
				},
				{
					"account": driver_advance_account,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": settlement_amount,
					"party_type": "Employee",
					"party": self.driver,
				},
			]
		else:
			accounts = [
				{
					"account": driver_advance_account,
					"debit_in_account_currency": settlement_amount,
					"credit_in_account_currency": 0,
					"party_type": "Employee",
					"party": self.driver,
				},
				{
					"account": cash_account,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": settlement_amount,
				},
			]

		jv = frappe.get_doc({
			"doctype": "Journal Entry",
			"voucher_type": "Cash Entry",
			"posting_date": frappe.utils.today(),
			"company": self.company,
			"accounts": accounts,
		})

		jv.insert(ignore_permissions=True)
		jv.submit()

		self.db_set("settlement_jv", jv.name)
		self.db_set("settlement_status", "Settled")
		self.db_set("balance_amount", 0)
		self.db_set("trip_status", "Settled")
@frappe.whitelist()
def create_settlejv(name):
    doc = frappe.get_doc("Trip", name)
    doc.create_settlement_jv()
    return "Settlement JV Created"
