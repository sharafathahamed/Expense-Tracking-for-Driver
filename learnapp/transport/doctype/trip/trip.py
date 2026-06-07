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
		rental_jv: DF.Link | None
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
				self.set_onload("default_driver_advance_amount", default_adv)
		
	def on_submit(self):
		self.create_advance_jv()
		self.create_rental_jv()
		self.update_expense_totals(self.get_initial_total_expense())
	
	def on_cancel(self):
		self.cancel_linked_jv(self.settlement_jv, "settlement_jv")
		self.cancel_linked_jv(self.rental_jv, "rental_jv")
		self.cancel_linked_jv(self.advance_jv, "advance_jv")
		self.db_set("trip_status", "Open")
		self.db_set("settlement_status", "Pending")
		self.db_set("balance_amount", 0)
		self.db_set("total_expense", 0)

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
            "user_remark": f"Advance given to Driver {driver_name} for Trip {self.name}",
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

	def create_rental_jv(self):
		if self.vehicle_type != "Rented Bus":
			return

		if self.rental_jv:
			return

		if not self.rental_amount or self.rental_amount <= 0:
			frappe.throw("Please enter rental amount for the rented bus")

		expense_account = self.get_rental_expense_account()
		cash_account = self.get_cash_account()
		owner = self.rental_owner or self.rented_vehicle_number or "Rental Vehicle"

		jv = frappe.get_doc({
			"doctype": "Journal Entry",
			"voucher_type": "Cash Entry",
			"posting_date": self.trip_date,
			"company": self.company,
			"user_remark": f"Rental expense paid to {owner} for Trip {self.name}",
			"accounts": [
				{
					"account": expense_account,
					"debit_in_account_currency": self.rental_amount,
					"credit_in_account_currency": 0,
				},
				{
					"account": cash_account,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": self.rental_amount,
				},
			],
		})
		jv.insert(ignore_permissions=True)
		jv.submit()

		self.db_set("rental_jv", jv.name)

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

	def get_rental_expense_account(self):
		company_accounts = frappe.db.get_value(
			"Company",
			self.company,
			["default_expense_account", "service_expense_account"],
			as_dict=True,
		)
		account = (company_accounts or {}).get("default_expense_account") or (company_accounts or {}).get("service_expense_account")
		if account:
			return account

		expense_accounts = frappe.get_all(
			"Account",
			filters={
				"company": self.company,
				"root_type": "Expense",
				"is_group": 0,
			},
			pluck="name",
			limit=1,
		)
		if expense_accounts:
			return expense_accounts[0]

		frappe.throw(f"Expense account is not available for company {self.company}")

	def get_rental_expense_component(self):
		if self.vehicle_type == "Rented Bus" and self.rental_jv and self.rental_amount:
			return self.rental_amount
		return 0

	def get_initial_total_expense(self):
		return self.get_rental_expense_component()

	def get_settlement_snapshot(self, total_expense=None):
		total_expense = total_expense if total_expense is not None else (self.total_expense or 0)
		driver_expense = total_expense - self.get_rental_expense_component()

		if driver_expense <= 0:
			return 0, "Pending"

		balance = (self.advance_given_to_driver or 0) - driver_expense
		if balance > 0:
			status = "Driver Owes Company"
		elif balance < 0:
			status = "Company Owes Driver"
		else:
			status = "Settled"

		return balance, status

	def update_expense_totals(self, total_expense):
		balance, status = self.get_settlement_snapshot(total_expense)
		self.db_set("total_expense", total_expense)
		self.db_set("balance_amount", balance)
		self.db_set("settlement_status", status)
	
	def on_update_after_submit(self):
		if self.settlement_jv and self.settlement_status!="Settled":
			jv_read=frappe.db.get_value("Journal Entry",self.settlement_jv,"total_debit")
			if jv_read:
				self.db_set("balance_amount", 0)
				self.db_set("settlement_status", "Settled")
				self.db_set("trip_status", "Settled")

	def create_settlement_jv(self):
		if self.settlement_jv:
			frappe.throw("Settlement JV is already created for this Trip.")

		if not self.balance_amount or self.balance_amount == 0:
			frappe.throw("Balance amount must be non-zero to create a settlement entry.")

		if self.settlement_status not in ("Company Owes Driver", "Driver Owes Company"):
			frappe.throw("Settlement JV can only be created when a balance is pending.")

		cash_account = self.get_cash_account()
		driver_advance_account = self.get_driver_advance_acc()
		driver_name=frappe.db.get_value("Employee",self.driver,"employee_name")
		settlement_amount = abs(self.balance_amount)

		if self.balance_amount < 0:
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
		else:
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
