import frappe

def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary

def get_columns():
    return [
        {
            "label": "Trip",
            "fieldname": "trip",
            "fieldtype":"Link",
            "options": "Trip"
        },
        {
            "label":"Trip Date",
            "fieldname":"trip_date",
            "fieldtype":"Date"
        },
        {
            "label":"Driver",
            "fieldname":"driver",
            "fieldtype":"Link",
            "options": "Employee"
        },
        {
            "label":"Driver Name",
            "fieldname":"driver_name",
            "fieldtype":"Data"
        },
        {
            "label":"Vehicle Type",
            "fieldname":"vehicle_type",
            "fieldtype":"Data"
        },
        {
            "label":"Advance Given",
            "fieldname":"advance_given",
            "fieldtype":"Currency"
        },
        {
            "label":"Actual Spent",
            "fieldname":"actual_spent",
            "fieldtype":"Currency"
        },
        {
            "label":"Difference",
            "fieldname":"difference",
            "fieldtype":"Currency"
        },
        {
            "label":"Advance Sufficient?",
            "fieldname":"advance_sufficient",
            "fieldtype":"Data"
        },
        {
            "label":"Settlement Status",
            "fieldname":"settlement_status",
            "fieldtype":"Data"
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)

    data = frappe.db.sql(f"""
        select t.name as trip, t.trip_date, t.driver,
		e.employee_name as driver_name,
		t.vehicle_type,
		t.advance_given_to_driver as advance_given,
		t.total_expense as actual_spent,
		t.rental_amount, t.rental_jv,
		t.settlement_status
        from `tabTrip` t
        inner join `tabEmployee` e on e.name = t.driver
        where
		t.docstatus = 1
		and t.total_expense > 0
		{conditions}
        order by
            t.trip_date desc
    """, filters, as_dict=True)

    for row in data:
        if row.vehicle_type == "Rented Bus" and row.rental_jv:
            row.actual_spent=(row.actual_spent or 0)-(row.rental_amount or 0)
        row.difference=(row.advance_given or 0)-(row.actual_spent or 0)
        diff=row.difference
        if diff>500:
            row.advance_sufficient="Excess Advance"
        elif diff>=0:
            row.advance_sufficient="Sufficient"
        elif diff>=-500:
            row.advance_sufficient="Slightly Low"
        else:
            row.advance_sufficient="Insufficient"
    return data

def get_summary(data):
    if not data:
        return []

    total_advance=sum(r.advance_given for r in data)
    total_spent=sum(r.actual_spent for r in data)
    total_diff=total_advance-total_spent
    insufficient_count=sum(1 for row in data if (row.difference)<0)
    excess_count=sum(1 for row in data if (row.difference)>0)
    adv=frappe.db.get_single_value("Transport Settings","default_driver_advance_amount")
    
    insufficient_trips=[abs(row.difference) for row in data if (row.difference)<0]
    if insufficient_trips:
        avg_increase=sum(insufficient_trips)/len(insufficient_trips)  
        adv_tobGiven= round(adv+avg_increase)
    else: 
        avg_increase=0

    excess_trips=[row.difference for row in data if (row.difference)>0]
    avg_reduce=sum(excess_trips)/len(excess_trips) if excess_trips else 0

    if total_diff<0:
        overall_status="Advance Not Sufficient"
    elif total_diff>0:
        overall_status="Advance More Than Needed"
    else:
        overall_status="Advance Exactly Sufficient"

    return [
        {
            "label":"Advance Status",
            "value":overall_status,
            "datatype":"Data",
            "indicator":"Red" if total_diff<0 else "Green",
        },
        {
            "label":"Trips with Insufficient Advance",
            "value":insufficient_count,
            "datatype":"Int",
            "indicator":"Red" if insufficient_count else "Green"
        },
        {
            "label":"Insufficient Trips",
            "value":avg_increase,
            "datatype":"Currency",
            "indicator":"Red" if avg_increase>0 else "Green"
        },
        {
            "label":"Advance to be Given",
            "value":adv_tobGiven,
            "datatype":"Currency",
        },
        {
            "label":"Trips with Excess Advance",
            "value":excess_count,
            "datatype":"Int",
            "indicator":"Orange" if excess_count else "Green"
        },
        {
            "label":"Excess Trips",
            "value":avg_reduce,
            "datatype":"Currency",
            "indicator":"Orange" if avg_reduce>0 else "Green"
        }
    ]

def get_chart(data):
    if not data:
        return None

    labels=[]
    advance_values=[]
    spent_values=[]

    for row in data:
        labels.append(f"{row.trip} ({row.driver_name})")
        advance_values.append(row.advance_given)
        spent_values.append(row.actual_spent)

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Advance Given", "values": advance_values},
                {"name": "Actual Spent", "values": spent_values}
            ]
        },
        "type": "bar",
        "title": "Advance vs Actual Expense per Trip"
    }

def get_conditions(filters):
    cond=""
    if filters.get("company"):
        cond+= " and t.company =%(company)s"
    if filters.get("from_date"):
        cond+= " and t.trip_date >=%(from_date)s"
    if filters.get("to_date"):
        cond +=" and t.trip_date<= %(to_date)s"
    if filters.get("driver"):
        cond +=" and t.driver=%(driver)s"
    if filters.get("settlement_status"):
        cond+= " and t.settlement_status = %(settlement_status)s"
    return cond
