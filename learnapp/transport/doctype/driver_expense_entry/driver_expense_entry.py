# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DriverExpenseEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from learnapp.transport.doctype.driver_expense_detail.driver_expense_detail import DriverExpenseDetail
		from frappe.types import DF

		amended_from: DF.Link | None
		company: DF.Link | None
		driver: DF.Link | None
		entry_date: DF.Date | None
		expense_details: DF.Table[DriverExpenseDetail]
		journal_entry: DF.Link | None
		total_amount: DF.Currency
		trip: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.calculate_total()

	def calculate_total(self):
		self.total_amount=sum(row.amount or 0 for row in self.expense_details)

	def on_submit(self):
		self.create_expense_jv()
		self.update_trip_totals()

	def on_cancel(self):
		if self.journal_entry:
			jv_doc=frappe.get_doc("Journal Entry",self.journal_entry)
			if jv_doc.docstatus == 1:
				jv_doc.cancel()
			self.db_set("journal_entry",None)
		self.reverse_trip_totals()


	def create_expense_jv(self):
		self.validate_expense()

		driver = frappe.db.get_value("Employee",self.driver,"employee_name")
		driver_adv_account=self.get_driv_adv_account()
		accounts=[]
		for row in self.expense_details:
			if not row.expense_account:
				frappe.throw(f"Row {row.idx}:Expense Account is missing.")
			if not row.amount or row.amount<=0:
				frappe.throw(f"Row {row.idx}:Amount should be greater than 0.")
			if not row.expense_category:
				frappe.throw(f"Row {row.idx}:Expense Category is missing.")
			accounts.append({
				"account":row.expense_account,
                "debit_in_account_currency":row.amount,
                "credit_in_account_currency":0
			})
		accounts.append({
			"account":driver_adv_account,
			"debit_in_account_currency":0,
			"credit_in_account_currency":self.total_amount,
			"party_type":"Employee",
			"party":self.driver
		})
		jv = frappe.get_doc({
			"doctype":"Journal Entry",
			"voucher_type": "Cash Entry",
            "posting_date": self.entry_date,
            "company": self.company,
            "accounts": accounts
		})
		jv.insert(ignore_permissions=True)
		jv.submit()

		self.db_set("journal_entry",jv.name)

	def update_trip_totals(self):
		trip=frappe.get_doc("Trip",self.trip)
		new_total=trip.total_expense+self.total_amount
		trip.update_expense_totals(new_total)

	def reverse_trip_totals(self):
		trip=frappe.get_doc("Trip",self.trip)
		new_total=max(trip.total_expense-self.total_amount,0)
		trip.update_expense_totals(new_total)
	
	def validate_expense(self):
		if not self.expense_details or len(self.expense_details)==0:
			frappe.throw("Atleast One expense is required")
		trip_status=frappe.db.get_value("Trip",self.trip,"trip_status")
		if trip_status not in ("On Trip","Completed"):
			frappe.throw(f"Cannot submit expenses. Trip status is '{trip_status}'")
	
	def get_driv_adv_account(self):
		account=frappe.db.get_value("Account",{
			"account_name":"Driver Advances",
            "company":self.company,
            "is_group":0
		},"name")
		if not account:
			frappe.throw("Driver Advances account not found. Check Chart of Accounts.")
		return account
