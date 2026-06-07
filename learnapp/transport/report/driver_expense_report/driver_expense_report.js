frappe.query_reports["Driver Expense Report"] = {
    filters: [
        {
            fieldname: "company",
            label: "Company",
            fieldtype: "Link",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company")
        },
        {
            fieldname:"from_date",
            label:"From Date",
            fieldtype:"Date",
            reqd:1,
            default:frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_end()
        },
        {
            fieldname:"driver",
            label: "Driver",
            fieldtype:"Link",
            options:"Employee",
            filters:{"designation":"Driver"}
        },
        {
            fieldname:"expense_happened_for",
            label: "Expense Happened For",
            fieldtype:"Select",
            options:"\nCompany - Vehicle & Asset\nCompany - Passenger Service\nDriver Personal Allowance",
        },
        {
            fieldname:"expense_category",
            label: "Expense Category",
            fieldtype:"Link",
            options:"Expense Category"
        }
    ]
};
