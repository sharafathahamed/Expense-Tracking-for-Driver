import frappe

def on_submit(doc, method):
	route = frappe.get_single("Stock Transfer Route Settings")
	
	for item in doc.items:
		t_warehouse = item.get("t_warehouse")
		if not t_warehouse:
			continue
		if t_warehouse != route.source_warehouse:
			continue
		qty = item.qty
		create_stock_entry("Material Issue", route.source_company, item.item_code, qty,
			s_warehouse=getDefWarehouse(route.source_company))

		create_stock_entry("Material Receipt", route.intermediate_company, item.item_code, qty,
			t_warehouse=getDefWarehouse(route.intermediate_company))

		create_stock_entry("Material Issue", route.intermediate_company, item.item_code, qty,
			s_warehouse=getDefWarehouse(route.intermediate_company))

		create_stock_entry("Material Receipt", route.destination_company, item.item_code, qty,
			t_warehouse=getDefWarehouse(route.destination_company))
		
def create_stock_entry(entry_type, company, item_code, qty, s_warehouse=None, t_warehouse=None):
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = entry_type
	se.company = company
	item = {"item_code": item_code, "qty": qty}
	if s_warehouse:
		item["s_warehouse"] = s_warehouse
	if t_warehouse:
		item["t_warehouse"] = t_warehouse
	se.append("items", item)
	se.insert()
	se.submit()
	return se

def getDefWarehouse(company):
	abbr = frappe.get_cached_value("Company", company, "abbr")
	return frappe.db.get_value("Warehouse", {"company": company, "warehouse_name": "Stores"}, "name") or f"Stores - {abbr}"