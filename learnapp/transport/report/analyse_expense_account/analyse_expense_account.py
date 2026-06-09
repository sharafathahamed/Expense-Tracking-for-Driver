# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    return columns, data, None, chart

def get_columns():
    return [
        {
            "label":"Expense Account",
            "fieldname": "expense_account",
            "fieldtype":"Link",
            "options": "Account",
            "width": 220
        },
        {
            "label": "Expense Category",
            "fieldname": "expense_category",
            "fieldtype": "Link",
            "options": "Expense Category",
            "width": 160
        },
        {
            "label": "No. of Transactions",
            "fieldname": "transaction_count",
            "fieldtype": "Int",
            "width": 140
        },
        {
            "label": "Total Amount Spent",
            "fieldname": "total_amount",
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "label": "Average Per Transaction",
            "fieldname": "avg_per_trip",
            "fieldtype": "Currency",
            "width": 170
        },
        {
            "label": "% of Total Expense",
            "fieldname": "percentage",
            "fieldtype": "Percent",
            "width": 140
        }
    ]

def get_data(filters):
    conditions=get_conditions(filters)

    data=frappe.db.sql(f"""
        select
            ded.expense_account,
            ded.expense_category,
            count(ded.name) as transaction_count,
            sum(ded.amount) as total_amount,
            avg(ded.amount) as avg_per_trip
        from `tabDriver Expense Detail` ded
        inner join `tabDriver Expense Entry` dee on dee.name= ded.parent
        where
            dee.docstatus = 1
            {conditions}
        group by ded.expense_account, ded.expense_category
        order by total_amount desc
    """, filters, as_dict=True)

    grand_total=sum(r.total_amount or 0 for r in data)

    for row in data:
        row.percentage = round((row.total_amount/grand_total* 100) if grand_total else 0, 2)

    return data

def get_conditions(filters):
    conditions = ""
    if filters.get("company"):
        conditions+= " and dee.company = %(company)s"
    if filters.get("from_date"):
        conditions+=" and dee.entry_date >= %(from_date)s"
    if filters.get("to_date"):
        conditions+= " and dee.entry_date <= %(to_date)s"
    if filters.get("expense_happened_for"):
        conditions += " and ded.expense_happened_for = %(expense_happened_for)s"
    if filters.get("expense_category"):
        conditions += " and ded.expense_category = %(expense_category)s"
    return conditions

def get_chart(data):
    if not data:
        return None
    return {
        "data": {
            "labels":[row.expense_account for row in data],
            "datasets":[{
                "name": "Amount Spent",
                "values": [row.total_amount for row in data]
            }]
        },
        "type": "bar",
        "title": "Expense Account Wise Spending"
    }
