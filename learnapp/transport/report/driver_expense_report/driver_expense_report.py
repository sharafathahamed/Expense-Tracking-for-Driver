# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters = None):
	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():

	return [
		{
			"label": "Date",
			"fieldname": "entry_date",
			"fieldtype": "Date",
		},
		{
			"label": "Trip",
			"fieldname": "trip",
			"fieldtype": "Link",
			"options":"Trip"
		},
		{
			"label": "Driver",
			"fieldname": "driver",
			"fieldtype": "Link",
			"options":"Employee"
		},
		{
			"label": "Expense Category",
			"fieldname": "expense_category",
			"fieldtype": "Data",
		},
		{
			"label": "Expense Account",
			"fieldname": "expense_account",
			"fieldtype": "Link",
			"options":"Account"
		},
		{
			"label": "Expense Happened For",
			"fieldname": "expense_happened_for",
			"fieldtype": "Data",
		},
		{
			"label": "Advance Given",
			"fieldname": "advance_given_to_driver",
			"fieldtype": "Currency",
		},
		{
			"label": "Total Expense",
			"fieldname": "total_expense",
			"fieldtype": "Currency",
		},
		{
			"label": "Balance",
			"fieldname": "balance",
			"fieldtype": "Currency",
		},
		{
			"label": "Settlement Status",
			"fieldname": "settlement_status",
			"fieldtype": "Data",
		}
	]


def get_data(filters):
    conditions=get_conditions(filters)
    data=frappe.db.sql(f"""
        SELECT
            dee.entry_date, dee.trip, dee.driver,
            ded.expense_category, ded.expense_account,
            ded.expense_happened_for, ded.amount,
            t.advance_given_to_driver, t.total_expense,
            t.balance_amount as balance, t.settlement_status
        FROM `tabDriver Expense Entry` dee
        INNER JOIN `tabDriver Expense Detail` ded ON ded.parent = dee.name
        INNER JOIN `tabTrip` t ON t.name = dee.trip
        WHERE
            dee.docstatus = 1
            {conditions}
        ORDER BY
            dee.entry_date DESC
    """, filters, as_dict=True)
    return data
    

def get_conditions(filters):
    conditions=""
    if filters.get("company"):
        conditions+=" and dee.company = %(company)s"

    if filters.get("driver"):
        conditions+=" and dee.driver = %(driver)s"

    if filters.get("from_date"):
        conditions+=" and dee.entry_date >= %(from_date)s"

    if filters.get("to_date"):
        conditions+=" and dee.entry_date <= %(to_date)s"

    if filters.get("trip"):
        conditions+=" and dee.trip = %(trip)s"
    return conditions