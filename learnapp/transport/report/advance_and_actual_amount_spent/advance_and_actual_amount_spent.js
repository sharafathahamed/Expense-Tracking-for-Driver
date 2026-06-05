frappe.query_reports["Advance and Actual Amount Spent"] = {
    filters: [
        {
            fieldname: "company",
            label: "Company",
            fieldtype:"Link",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company")
        },
        {
            fieldname:"from_date",
            label:"From Date",
            fieldtype:"Date",
            reqd:1,
            default:frappe.datetime.year_start()
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.now_date()
        },
        {
            fieldname:"driver",
            label:"Driver",
            fieldtype: "Link",
            options:"Employee",
            filters:{"designation": "Driver"}
        },
        {
            fieldname:"settlement_status",
            label: "Settlement Status",
            fieldtype:"Select",
            options:"\nPending\nDriver Owes Company\nCompany Owes Driver\nSettled"
        }
    ]
};