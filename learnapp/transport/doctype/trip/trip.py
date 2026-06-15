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

	
	def validate(self):
		self.validate_vehicle_info()
		self.check_duplicate_trip()

	def validate_vehicle_info(self):
		if self.vehicle_type=="Own Bus":
			if not self.bus_asset:
				frappe.throw("Bus Asset is required for Own Bus trips.")
		elif self.vehicle_type=="Rented Bus":
			if not self.rented_vehicle_number:
				frappe.throw("Rented Vehicle Number is required for Rented Bus trips.")
			if not self.rental_amount or self.rental_amount<=0:
				frappe.throw("Rental Amount is required for Rented Bus trips.")

	def check_duplicate_trip(self):
		existing=frappe.db.exists("Trip",{
			"driver":self.driver,
			"trip_date":self.trip_date,
			"trip_status":["in",["Open","On Trip"]],
			"name":["!=",self.name]
		})
		if existing:
			frappe.throw(f"Driver already has an active trip ({existing}) on {self.trip_date}.")

	def onload(self):
		if not self.advance_given_to_driver:
			default_adv=frappe.db.get_single_value("Transport Settings","default_driver_advance_amount")
			if default_adv:
				self.set_onload("default_driver_advance_amount",default_adv)

	def on_submit(self):
		self.create_advance_jv()
		self.create_rental_jv()

	def on_cancel(self):
		self.cancel_driver_expense_entries()
		self.cancel_linked_jv(self.settlement_jv,"settlement_jv")
		self.cancel_linked_jv(self.rental_jv,"rental_jv")
		self.cancel_linked_jv(self.advance_jv,"advance_jv")
		frappe.db.set_value("Trip",self.name,{
			"trip_status":"Open",
			"settlement_status":"Pending",
			"balance_amount":0,
			"total_expense":0
		})

	def cancel_driver_expense_entries(self):
		entries=frappe.get_all("Driver Expense Entry",filters={
			"trip":self.name,
			"docstatus":1
		},pluck="name")
		for name in entries:
			doc=frappe.get_doc("Driver Expense Entry",name)
			doc.cancel()

	def cancel_linked_jv(self,jv_name,fieldname):
		if not jv_name:
			return
		jv_doc=frappe.get_doc("Journal Entry",jv_name)
		if jv_doc.docstatus==1:
			jv_doc.cancel()
		frappe.db.set_value("Trip",self.name,fieldname,None)

	def create_advance_jv(self):
		if not self.advance_given_to_driver or self.advance_given_to_driver<=0:
			frappe.throw("Please enter advance given to driver")
		driver_name=frappe.db.get_value("Employee",self.driver,"employee_name")
		cash_account=self.get_cash_account()
		driver_advance_acc=self.get_driver_advance_acc()
		jv=frappe.get_doc({
			"doctype":"Journal Entry",
			"voucher_type":"Cash Entry",
			"posting_date":self.trip_date,
			"company":self.company,
			"accounts":[
				{
					"account":driver_advance_acc,
					"debit_in_account_currency":self.advance_given_to_driver,
					"credit_in_account_currency":0,
					"party_type":"Employee",
					"party":self.driver
				},
				{
					"account":cash_account,
					"debit_in_account_currency":0,
					"credit_in_account_currency":self.advance_given_to_driver
				}
			]
		})
		jv.insert()
		jv.submit()
		frappe.db.set_value("Trip",self.name,{
			"advance_jv":jv.name,
			"trip_status":"On Trip"
		})

	def create_rental_jv(self):
		if self.vehicle_type!="Rented Bus":
			return
		if self.rental_jv:
			return
		owner=self.rental_owner or self.rented_vehicle_number or "Rental Vehicle"
		cash_account=self.get_cash_account()
		vehicle_hire_account=self.get_vehicle_hire_account()
		jv=frappe.get_doc({
			"doctype":"Journal Entry",
			"voucher_type":"Cash Entry",
			"posting_date":self.trip_date,
			"company":self.company,
			"user_remark":f"Rental expense paid to {owner} for Trip {self.name}",
			"accounts":[
				{
					"account":vehicle_hire_account,
					"debit_in_account_currency":self.rental_amount,
					"credit_in_account_currency":0
				},
				{
					"account":cash_account,
					"debit_in_account_currency":0,
					"credit_in_account_currency":self.rental_amount
				}
			]
		})
		jv.insert()
		jv.submit()
		frappe.db.set_value("Trip",self.name,"rental_jv",jv.name)

	def update_expense_totals(self,new_total):
		rental_component=self.rental_amount if self.vehicle_type=="Rented Bus" and self.rental_jv else 0
		driver_expense=new_total-rental_component

		if driver_expense<=0:
			balance=0
			status="Pending"
		else:
			balance=(self.advance_given_to_driver or 0)-driver_expense
			if balance>0:
				status="Driver Owes Company"
			elif balance<0:
				status="Company Owes Driver"
			else:
				status="Settled"

		frappe.db.set_value("Trip",self.name,{
			"total_expense":new_total,
			"balance_amount":balance,
			"settlement_status":status
		})

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
			frappe.throw("Driver Advances account not found. Check Chart of Accounts.")
		return account
	
	def get_vehicle_hire_account(self):
		account=frappe.db.get_value("Account",{
			"account_name":"Vehicle Hire Charges",
			"company":self.company,
			"is_group":0,
		},"name")
		if not account:
			frappe.throw("Vehicle Hire Charges account not found. Check Chart of Accounts.")
		return account

	def on_update_after_submit(self):
		if self.settlement_jv and self.settlement_status!="Settled":
			jv_docstatus=frappe.db.get_value("Journal Entry",self.settlement_jv,"docstatus")
			if jv_docstatus==1:
				frappe.db.set_value("Trip",self.name,{
					"balance_amount":0,
					"settlement_status":"Settled",
					"trip_status":"Settled"
				})

	def create_settlement_jv(self):
		if self.settlement_jv:
			frappe.throw("Settlement JV is already created for this Trip.")
		if not self.balance_amount or self.balance_amount==0:
			frappe.throw("Balance amount must be non-zero to create a settlement entry.")
		if self.settlement_status not in ("Company Owes Driver","Driver Owes Company"):
			frappe.throw("Settlement JV can only be created when a balance is pending.")

		cash_account=self.get_cash_account()
		driver_advance_account=self.get_driver_advance_acc()
		driver_name=frappe.db.get_value("Employee",self.driver,"employee_name")
		settlement_amount=abs(self.balance_amount)

		if self.balance_amount<0:
			accounts=[
				{
					"account":driver_advance_account,
					"debit_in_account_currency":settlement_amount,
					"credit_in_account_currency":0,
					"party_type":"Employee",
					"party":self.driver
				},
				{
					"account":cash_account,
					"debit_in_account_currency":0,
					"credit_in_account_currency":settlement_amount
				}
			]
		else:
			accounts=[
				{
					"account":cash_account,
					"debit_in_account_currency":settlement_amount,
					"credit_in_account_currency":0
				},
				{
					"account":driver_advance_account,
					"debit_in_account_currency":0,
					"credit_in_account_currency":settlement_amount,
					"party_type":"Employee",
					"party":self.driver
				}
			]

		jv=frappe.get_doc({
			"doctype":"Journal Entry",
			"voucher_type":"Cash Entry",
			"posting_date":frappe.utils.today(),
			"company":self.company,
			"accounts":accounts
		})
		jv.insert()
		jv.submit()
		frappe.db.set_value("Trip",self.name,{"settlement_jv":jv.name,"settlement_status":"Settled","balance_amount":0,"trip_status":"Settled"})

@frappe.whitelist()
def create_settlejv(name):
	doc=frappe.get_doc("Trip",name)
	doc.create_settlement_jv()
	return "Settlement JV Created"
