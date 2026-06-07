frappe.ui.form.on("Driver Expense Entry", {
	refresh: function(frm) {
		set_category_query(frm);
		set_expense_acc_query(frm);
	},
	trip: function(frm){
        if(frm.doc.trip){
            frappe.db.get_value("Trip",frm.doc.trip,["driver","company"],function(val){
                frm.set_value("driver",val.driver);
                frm.set_value("company",val.company);
                set_expense_acc_query(frm);
            });
        }
    }
});
frappe.ui.form.on("Driver Expense Detail",{
    amount:function(frm){
        calculate_total(frm);
    },
    expense_details_remove:function(frm){
        calculate_total(frm);
    },
    expense_happened_for:function(frm,cdt,cdn){
        frappe.model.set_value(cdt,cdn,"expense_category",null);
        frappe.model.set_value(cdt,cdn,"expense_account",null);
        frm.refresh_field("expense_details");
    },
    expense_category:function(frm,cdt,cdn){
        let row=locals[cdt][cdn];
        if(!row.expense_category || !frm.doc.company) return;
        frappe.db.get_value("Expense Category",row.expense_category,"default_account_name",function(val){
            if(!val || !val.default_account_name) return;
            frappe.db.get_value("Account",{
                "account_name":val.default_account_name,
                "company":frm.doc.company,
                "is_group":0
            },"name",function(acc){
                if(acc && acc.name){
                    frappe.model.set_value(cdt,cdn,"expense_account",acc.name);
                }
            });
        });
    }
});
function set_category_query(frm){
    frm.set_query("expense_category","expense_details",function(doc,cdt,cdn) {
        let row=locals[cdt][cdn];
        if(!row.expense_happened_for){
            return{
                filters:{
                    "name":""
                }
            };
        }
        return{
            filters:{
                "expense_type":row.expense_happened_for
            }
        };
    });
}
function set_expense_acc_query(frm){
	frm.set_query("expense_account","expense_details",function() {
		return{
			filters:{
				company:frm.doc.company,
				root_type:"Expense",
				parent_account:["like","Transportation%"],
				is_group:0
			}
		};
	});
}
function calculate_total(frm){
    let total=0;
    let rows=frm.doc.expense_details;
    for(let i=0;i<rows.length;i++){
        total+=flt(rows[i].amount)
    }
    frm.set_value("total_amount",total)
    frm.refresh_field("total_amount")
}
