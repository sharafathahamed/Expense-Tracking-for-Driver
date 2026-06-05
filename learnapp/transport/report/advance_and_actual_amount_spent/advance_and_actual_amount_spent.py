import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    summary = get_summary(data)
    chart = get_chart(data)
    return columns, data, summary, chart

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
		t.advance_given_to_driver as advance_given,
		t.total_expense as actual_spent, 
		(t.advance_given_to_driver - t.total_expense) as difference, t.settlement_status
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
        diff=row.difference or 0
        if diff>500:
            row.advance_sufficient = "Excess Advance"
        elif diff>=0:
            row.advance_sufficient = "Sufficient"
        elif diff>=-500:
            row.advance_sufficient = "Slightly Low"
        else:
            row.advance_sufficient = "Insufficient"

    return data

def get_summary(data):
    total_advance = sum(r.advance_given for r in data)
    total_spent = sum(r.actual_spent for r in data)
    total_diff = total_advance - total_spent
    insufficient_count = sum(
        1 for r in data if r.difference < 0 
    )

    return [
        {
            "label":"Total Advance Given",
            "value": total_advance,
            "datatype":"Currency"
        },
        {
            "label":"Total Actually Spent",
            "value":total_spent,
            "datatype": "Currency"
        },
        {
            "label":"Net Balance",
            "value": total_diff,
            "datatype": "Currency"
        },
        {
            "label":"Trips with Insufficient Advance",
            "value":insufficient_count,
            "datatype":"Int"
        }
    ]

def get_chart(data):
    if not data:
        return None
    return{
        "data":{
            "labels":[r.trip for r in data],
            "datasets": [
                {
                    "name":"Advance Given",
                    "values": [r.advance_given for r in data]
                },
                {
                    "name":"Actual Spent",
                    "values":[r.actual_spent for r in data]
                }
            ]
        },
        "type":"bar", "title":"Advance vs Actual Spent Per Trip"
    }

def get_conditions(filters):
    cond=""
    if filters.get("company"):
        cond+= " AND t.company =%(company)s"
    if filters.get("from_date"):
        cond+= " AND t.trip_date >=%(from_date)s"
    if filters.get("to_date"):
        cond +=" AND t.trip_date<= %(to_date)s"
    if filters.get("driver"):
        cond +=" AND t.driver=%(driver)s"
    if filters.get("settlement_status"):
        cond+= " AND t.settlement_status = %(settlement_status)s"
    return cond
