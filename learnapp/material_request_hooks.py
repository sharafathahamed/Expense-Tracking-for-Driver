import frappe


def on_stock_entry_submit(doc, method):
	route = frappe.get_single("Stock Transfer Route Settings")

	if doc.stock_entry_type == "Material Issue":
		return

	matched_items = []
	for item in doc.items:
		if item.t_warehouse == route.source_warehouse and item.qty > 0:
			matched_items.append({"item_code": item.item_code, "qty": item.qty})

	if not matched_items:
		return

	run_transfer_chain(matched_items)


def on_purchase_receipt_submit(doc, method):
	route = frappe.get_single("Stock Transfer Route Settings")

	matched_items = []
	for item in doc.items:
		if item.warehouse == route.source_warehouse and item.qty > 0:
			matched_items.append({"item_code": item.item_code, "qty": item.qty})

	if not matched_items:
		return

	run_transfer_chain(matched_items)


def on_stock_reconciliation_submit(doc, method):
	route = frappe.get_single("Stock Transfer Route Settings")

	matched_items = []
	for item in doc.items:
		if item.warehouse == route.source_warehouse and item.qty and item.qty > 0:
			matched_items.append({"item_code": item.item_code, "qty": item.qty})

	if not matched_items:
		return

	run_transfer_chain(matched_items)


def run_transfer_chain(matched_items):
	route = frappe.get_single("Stock Transfer Route Settings")
	intermediate_warehouse = getDefWarehouse(route.intermediate_company)

	create_stock_entry("Material Issue", route.source_company, matched_items, s_warehouse=route.source_warehouse)
	create_stock_entry("Material Receipt", route.intermediate_company, matched_items, t_warehouse=intermediate_warehouse)
	create_stock_entry("Material Issue", route.intermediate_company, matched_items, s_warehouse=intermediate_warehouse)
	create_stock_entry("Material Receipt", route.destination_company, matched_items, t_warehouse=route.destination_warehouse)


def create_stock_entry(entry_type, company, items, s_warehouse=None, t_warehouse=None):
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = entry_type
	se.company = company
	for it in items:
		row = {"item_code": it["item_code"], "qty": it["qty"], "allow_zero_valuation_rate": 1}
		if s_warehouse:
			row["s_warehouse"] = s_warehouse
		if t_warehouse:
			row["t_warehouse"] = t_warehouse
		se.append("items", row)
	se.insert(ignore_permissions=True)
	se.submit()
	return se


def getDefWarehouse(company):
	abbr = frappe.get_cached_value("Company", company, "abbr")
	return frappe.db.get_value("Warehouse", {"company": company, "warehouse_name": "Stores"}, "name") or f"Stores - {abbr}"