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
            "fieldtype": "Link",
            "options": "Expense Category"
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
        ded.expense_category,
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
    bill_seen={}
    driver_day_totals ={}
    driver_day_personal ={}
    driver_day_misc ={}
    result= []

    for row in raw:
        day_key = f"{row.driver}_{row.entry_date}"
        driver_day_totals[day_key] = driver_day_totals.get(day_key, 0)+(row.amount or 0)

        if row.expense_happened_for=="Driver Personal Allowance":
            driver_day_personal[day_key]=driver_day_personal.get(day_key, 0)+1

        if row.expense_category=="Miscellaneous":
            driver_day_misc[day_key]=driver_day_misc.get(day_key, 0)+1

        if row.billreceipt_no:
            bill_key=f"{row.driver}_{str(row.billreceipt_no).strip()}"
            bill_seen[bill_key]=bill_seen.get(bill_key, 0) + 1

    for row in raw:
        defect=[]
        threshold=thresh.get(row.expense_category)
        day_key=f"{row.driver}_{row.entry_date}"

        if threshold and row.amount >threshold:
            defect.append(f"High amount (limit ₹{threshold})")

        if not row.billreceipt_no and row.amount >200:
            defect.append("No bill/receipt")

        key = f"{row.driver}_{row.entry_date}_{row.expense_category}"
        if key in seen:
            defect.append("Duplicate category same day")
        else:
            seen[key]=True

        if (row.expense_happened_for=="Driver Personal Allowance" and row.amount> 500):
            defect.append("High personal expense")

        if row.billreceipt_no:
            bill_key=f"{row.driver}_{str(row.billreceipt_no).strip()}"
            if bill_seen.get(bill_key, 0)>1:
                defect.append("Repeated bill/receipt number")

        if (
            not row.billreceipt_no
            and row.amount>=500
            and float(row.amount).is_integer()
            and int(row.amount)%100==0
        ):
            defect.append("Rounded amount without bill")

        if (
            row.expense_happened_for=="Driver Personal Allowance"
            and driver_day_personal.get(day_key, 0) > 1
        ):
            defect.append("Multiple personal claims same day")

        if row.expense_category == "Miscellaneous" and driver_day_misc.get(day_key, 0) > 1:
            defect.append("Multiple miscellaneous claims same day")

        if driver_day_totals.get(day_key, 0) > 7000:
            defect.append("High total claimed in a single day")

        if defect:
            row.anomaly=" | ".join(defect)
            result.append(row)

    return result

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
    if filters.get("expense_happened_for"):
        cond += " AND ded.expense_happened_for = %(expense_happened_for)s"
    if filters.get("expense_category"):
        cond += " AND ded.expense_category = %(expense_category)s"
    return cond
