# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {
            "label":"Date",
            "fieldname": "entry_date",
            "fieldtype":"Date"
        },
        {
            "label":"Trip",
            "fieldname": "trip",
            "fieldtype": "Link",
            "options":"Trip"
        },
        {
            "label": "Driver",
            "fieldname": "driver",
            "fieldtype": "Link",
            "options": "Employee"
        },
        {
            "label": "Driver Name",
            "fieldname": "driver_name",
            "fieldtype": "Data"
        },
        {
            "label": "Expense Category",
            "fieldname": "expense_category",
            "fieldtype": "Data"
        },
        {
            "label": "Amount",
            "fieldname": "amount",
            "fieldtype": "Currency"
        },
        {
            "label": "Bill No",
            "fieldname": "billreceipt_no",
            "fieldtype": "Data"
        },
        {
            "label": "Expense Happened For",
            "fieldname": "expense_happened_for",
            "fieldtype": "Data"
        },
        {
            "label": "Anomaly",
            "fieldname": "anomaly",
            "fieldtype": "Data"
        }
    ]

def get_data(filters):
    cond = get_conditions(filters)

    raw = frappe.db.sql(f"""
        select dee.entry_date, dee.trip,dee.driver,
        e.employee_name as driver_name,
        ded.expense_category_v_a, ded.expense_category_p_s, ded.expense_category_d_p,
        ded.amount, ded.billreceipt_no, ded.expense_happened_for,
        dee.name as expense_entry
        from `tabDriver Expense Detail` ded
        inner join `tabDriver Expense Entry` dee ON dee.name= ded.parent
        inner join `tabEmployee` e ON e.name= dee.driver
        where dee.docstatus = 1 {cond}
        order by dee.entry_date desc
    """, filters, as_dict=True)

    thresh = {
        "Fuel":3000,
        "Driver Food & Tea": 200,
        "Driver Accommodation":1000,
        "Passenger Water & Snacks":500,
        "Puncture":800,
        "Vehicle Repair & Maintenance":5000,
        "Toll & Parking":500,
        "Miscellaneous": 300
    }

    seen= {}
    result= []

    for row in raw:
        defect=[]
        row.expense_category = get_expense_category(row)

        for category in get_all_expense_categories(row):
            threshold = thresh.get(category)
            if threshold and row.amount > threshold:
                defect.append(f"High amount (limit ₹{threshold})")
                break

        if not row.billreceipt_no and row.amount > 200:
            defect.append("No bill/receipt")

        key = f"{row.driver}_{row.entry_date}_{row.expense_category}"
        if key in seen:
            defect.append("Duplicate category same day")
        else:
            seen[key] = True

        if (row.expense_happened_for == "Driver Personal Allowance" and row.amount> 500):
            defect.append("High personal expense")

        if defect:
            row.anomaly=" | ".join(defect)
            result.append(row)

    return result


def get_expense_category(row):
    category_map = {
        "Company - Vehicle & Asset": row.expense_category_v_a,
        "Company - Passenger Service": row.expense_category_p_s,
        "Driver Personal Allowance": row.expense_category_d_p,
    }
    return category_map.get(row.expense_happened_for) or next(
        (
            category
            for category in get_all_expense_categories(row)
            if category
        ),
        None,
    )


def get_all_expense_categories(row):
    return [
        row.expense_category_v_a,
        row.expense_category_p_s,
        row.expense_category_d_p,
    ]

def get_conditions(filters):
    cond = ""
    if filters.get("company"):
        cond+=" AND dee.company = %(company)s"
    if filters.get("from_date"):
        cond+= " AND dee.entry_date >= %(from_date)s"
    if filters.get("to_date"):
        cond+= " AND dee.entry_date <= %(to_date)s"
    if filters.get("driver"):
        cond +=" AND dee.driver = %(driver)s"
    return cond
