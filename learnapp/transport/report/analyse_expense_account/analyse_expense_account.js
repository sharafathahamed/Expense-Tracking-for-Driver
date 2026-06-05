frappe.query_reports["Analyse Expense Account"] = {
    filters: [
        {
            fieldname: "company",
            label: "Company",
            fieldtype: "Link",
            options: "Company",
            reqd:1
        },
        {
            fieldname:"from_date",
            label: "From Date",
            fieldtype:"Date",
            reqd: 1,
            default:frappe.datetime.month_start()
        },
        {
            fieldname:"to_date",
            label:"To Date",
            fieldtype: "Date",
            reqd:1,
            default:frappe.datetime.month_end()
        },
        {
            fieldname:"expense_happened_for",
            label: "Borne By",
            fieldtype:"Select",
            options:"\nCompany - Vehicle & Asset\nCompany - Passenger Service\nDriver Personal Allowance"
        }
    ]
};