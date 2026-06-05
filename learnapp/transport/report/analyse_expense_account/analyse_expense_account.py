# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    return columns, data, None, chart

def get_columns():
    return [
        {
            "label": "Expense Account",
            "fieldname": "expense_account",
            "fieldtype": "Link",
            "options": "Account",
        },
        {
            "label": "No. of Transactions",
            "fieldname": "transaction_count",
            "fieldtype": "Int",
        },
        {
            "label": "Total Amount Spent",
            "fieldname": "total_amount",
            "fieldtype": "Currency"
        },
        {
            "label": "Average Per Trip",
            "fieldname": "avg_per_trip",
            "fieldtype": "Currency"
        },
        {
            "label": "% of Total Expense",
            "fieldname": "percentage",
            "fieldtype": "Percent"
        }
    ]

def get_data(filters):
    conditions= get_conditions(filters)

    sqll=frappe.db.sql(f"""
        select 
            ded.expense_account,
            count(ded.name) as transaction_count,
            sum(ded.amount) as total_amount,
            avg(ded.amount) as avg_per_trip
        from `tabDriver Expense Detail` ded
        inner join `tabDriver Expense Entry` dee on dee.name= ded.parent
        where
            dee.docstatus = 1
            {conditions}
        group by ded.expense_account
        order by total_amount desc
    """, filters, as_dict=True)
    grand_total=sum(r.total_amount or 0 for r in sqll)

    for row in sqll:
        row.percentage = round((row.total_amount/grand_total* 100) if grand_total else 0, 2)

    return sqll

def get_conditions(filters):
    conditions = ""
    if filters.get("company"):
        conditions+= " AND dee.company = %(company)s"
    if filters.get("from_date"):
        conditions+=" AND dee.entry_date >= %(from_date)s"
    if filters.get("to_date"):
        conditions+= " AND dee.entry_date <= %(to_date)s"
    if filters.get("expense_happened_for"):
        conditions += " AND ded.expense_happened_for = %(expense_happened_for)s"
    return conditions

def get_chart(data):
    if not data:
        return None
    return {
        "data": {
            "labels":[r.expense_account for r in data],
            "datasets":[{
                "name": "Amount Spent",
                "values": [r.total_amount for r in data]
            }]
        },"type": "bar","title": "Expense Account Wise Spending"
    }
