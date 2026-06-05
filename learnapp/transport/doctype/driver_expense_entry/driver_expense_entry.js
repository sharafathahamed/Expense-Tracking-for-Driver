frappe.ui.form.on("Driver Expense Entry", {
	refresh: function(frm) {
		set_expense_acc_query(frm);
	},
	trip: function(frm){
        if(frm.doc.trip){
            frappe.db.get_value("Trip",frm.doc.trip,"driver",function(val){
                frm.set_value("driver",val.driver);
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
    }
});
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
