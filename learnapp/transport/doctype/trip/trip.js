// Copyright (c) 2026, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Trip", {
	refresh: function(frm) {
        advance_fetch(frm);
        filterfor_driver(frm);
        filterfor_transport(frm);
        create_btn_forsettle(frm);
    }
});
function create_btn_forsettle(frm) {
    if (
        frm.doc.docstatus === 1 &&
        ["Company Owes Driver", "Driver Owes Company"].includes(frm.doc.settlement_status) &&
        !frm.doc.settlement_jv
    ) {
        frm.add_custom_button("Create Settlement JV", function() {
            frappe.call({
                method: "frappe.transportation.doctype.trip.trip.create_settlejv",
                args: { name: frm.doc.name },
                callback: function(r) {
                    if (!r.exc) {
                        frappe.msgprint("Settlement JV Created.");
                        frm.reload_doc();
                    }
                }
            });
        });
    }
}
function advance_fetch(frm){
    if(frm.is_new() && !frm.doc.advance_given_to_driver){
        frappe.db.get_single_value(
            "Transport Settings","default_driver_advance_amount"
        ).then(value =>{
            if(value){
                frm.set_value("advance_given_to_driver",value);
            }
        });
    }
}
function filterfor_driver(frm){
    frm.set_query("driver", function() {
        return {
            filters: {
                "designation": "Driver",
                "status": "Active"
            }
        };
    });
}
function filterfor_transport(frm){
    frm.set_query("bus_asset", function() {
        return {
            filters: {
                "asset_category": "Transport"
            }
        };
    });
}
