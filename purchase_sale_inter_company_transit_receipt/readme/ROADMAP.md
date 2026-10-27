Partial deliveries depend on the receipt synchronisation of
`purchase_sale_inter_company`, unchanged by this module: the next
delivery must be synchronised with the open backorder of the receipt,
and a delivery without backorder must only cancel the rest of the
receipt (OCA/multi-company 14.0 since `c7861ab3`).
