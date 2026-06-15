import frappe

def on_submit(doc,method):
    if doc.material_request_type!="Purchase":
        return
    route= frappe.get_single("Stock Transfer Route Settings")
    
    if doc.company!=route.destination_company:
        return
    itemsForPurchase=[]
    for item in doc.items:
        itemsForPurchase.append({
            "item_code":item.item_code,
            "qty":item.qty,
            "rate":route.default_rate,
            "schedule_date":frappe.utils.nowdate(),
            "warehouse":getDefWarehouse(route.intermediate_company)
        })
    poCreate=create_po(
        company=route.intermediate_company,
		supplier=route.source_company,
		items=itemsForPurchase
    )

    so_a = create_inter_company_so(poCreate.name)

    if so_a:
        create_delivery_note(so_a.name)

def create_po(company,supplier,items):
    po=frappe.new_doc("Purchase Order")
    po.company=company
    po.supplier=supplier
    for item in items:
        po.append("items",item)
    po.run_method("set_missing_values")
    po.insert(ignore_permissions=True)
    po.submit()
    return po

def create_inter_company_so(po_name):
	from erpnext.buying.doctype.purchase_order.purchase_order import make_inter_company_sales_order
	route = frappe.get_single("Stock Transfer Route Settings")
	so = make_inter_company_sales_order(po_name)
	source_warehouse = getDefWarehouse(route.source_company)
	for item in so.items:
		if not item.delivery_date:
			item.delivery_date = frappe.utils.nowdate()
		if not item.warehouse:
			item.warehouse = source_warehouse
	so.insert(ignore_permissions=True)
	so.submit()
	return so

def create_delivery_note(sales_order_name):
	from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
	dn = make_delivery_note(sales_order_name)
	dn.insert(ignore_permissions=True)
	dn.submit()
	return dn


def getDefWarehouse(company):
	abbr=frappe.get_cached_value("Company", company, "abbr")
	return frappe.db.get_value("Warehouse",{"company": company,"warehouse_name":"Stores"},"name") or f"Stores - {abbr}"