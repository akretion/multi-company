# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import Form

from odoo.addons.account_invoice_inter_company.tests.test_inter_company_invoice import (
    TestAccountInvoiceInterCompanyBase,
)


class TestPurchaseSaleInterCompanyTransitReceipt(TestAccountInvoiceInterCompanyBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context={"test_queue_job_no_delay": 1})
        if "company_ids" in cls.env["res.partner"]._fields:
            cls.partner_company_a.company_ids = False
            cls.partner_company_b.company_ids = False
        cls.warehouse_a = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company_a.id)]
        )
        cls.company_a.sync_picking = True
        cls.company_a.sync_picking_transit_receipt = True
        cls.company_b.so_from_po = True
        cls.company_b.warehouse_id = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company_b.id)]
        )
        cls.intercompany_sale_user = cls.user_company_b.copy()
        cls.intercompany_sale_user.company_ids |= cls.company_a
        cls.company_b.intercompany_sale_user_id = cls.intercompany_sale_user
        for user in cls.user_company_a | cls.user_company_b:
            user.groups_id |= cls.env.ref(
                "sales_team.group_sale_manager"
            ) | cls.env.ref("purchase.group_purchase_manager")
        cls.env["product.pricelist"].sudo().search([]).write(
            {"currency_id": cls.env.ref("base.USD").id}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Consumable Product", "type": "consu"}
        )
        cls.serial_product = cls.env["product.product"].create(
            {"name": "Serial Product", "type": "product", "tracking": "serial"}
        )
        cls.serials = cls.env["stock.production.lot"]
        for name in ("111", "222", "333"):
            serial = cls.serials.create(
                {
                    "product_id": cls.serial_product.id,
                    "name": name,
                    "company_id": cls.company_b.id,
                }
            )
            cls.env["stock.quant"].create(
                {
                    "product_id": cls.serial_product.id,
                    "location_id": cls.company_b.warehouse_id.lot_stock_id.id,
                    "quantity": 1,
                    "lot_id": serial.id,
                }
            )
            cls.serials |= serial

    def _create_purchase_order(self, partner, product=None):
        purchase_form = Form(self.env["purchase.order"])
        purchase_form.company_id = self.company_a
        purchase_form.partner_id = partner
        with purchase_form.order_line.new() as line_form:
            line_form.product_id = product or self.product
            line_form.product_qty = 3.0
            line_form.price_unit = 450.0
        return purchase_form.save()

    def _approve_po(self, purchase):
        purchase.with_user(self.intercompany_sale_user).button_approve()
        return (
            self.env["sale.order"]
            .with_user(self.user_company_b)
            .search([("auto_purchase_order_id", "=", purchase.id)])
        )

    def _ship(self, sale, quantity, backorder=True):
        delivery = sale.picking_ids.filtered(lambda p: p.state != "done")
        delivery.move_lines.quantity_done = quantity
        res = delivery.with_user(self.user_company_b).button_validate()
        if isinstance(res, dict):
            wizard = Form(
                self.env[res["res_model"]].with_context(**res["context"])
            ).save()
            if backorder:
                wizard.process()
            else:
                wizard.process_cancel_backorder()

    def _ship_serials(self, sale, serials):
        delivery = sale.picking_ids
        move = delivery.move_lines
        move_line_vals = move._prepare_move_line_vals()
        move.move_line_ids = [(5, 0, 0)] + [
            (0, 0, dict(move_line_vals, qty_done=1, lot_id=serial.id))
            for serial in serials
        ]
        delivery.with_user(self.user_company_b).button_validate()

    def _validate_without_backorder(self, picking):
        res = picking.button_validate()
        Form(
            self.env[res["res_model"]].with_context(**res["context"])
        ).save().process_cancel_backorder()

    def _physical_receipts(self, purchase):
        return purchase.picking_ids.move_lines.move_dest_ids.picking_id

    def test_group_company_purchase_gets_transit_receipt_type(self):
        purchase = self._create_purchase_order(self.partner_company_b)
        self.assertEqual(purchase.picking_type_id, self.warehouse_a.transit_in_type_id)

    def test_other_supplier_purchase_keeps_receipt_type(self):
        supplier = self.env["res.partner"].create({"name": "Supplier"})
        purchase = self._create_purchase_order(supplier)
        self.assertEqual(purchase.picking_type_id, self.warehouse_a.in_type_id)

    def test_sync_picking_without_transit_receipt_keeps_receipt_type(self):
        self.company_a.sync_picking_transit_receipt = False
        purchase = self._create_purchase_order(self.partner_company_b)
        self.assertEqual(purchase.picking_type_id, self.warehouse_a.in_type_id)

    def test_transit_receipt_requires_sync_picking(self):
        self.company_a.sync_picking = False
        purchase = self._create_purchase_order(self.partner_company_b)
        self.assertEqual(purchase.picking_type_id, self.warehouse_a.in_type_id)

    def test_seller_without_sale_from_purchase_keeps_receipt_type(self):
        self.company_b.so_from_po = False
        purchase = self._create_purchase_order(self.partner_company_b)
        self.assertEqual(purchase.picking_type_id, self.warehouse_a.in_type_id)

    def test_seller_delivery_validates_transit_receipt(self):
        purchase = self._create_purchase_order(self.partner_company_b)
        sale = self._approve_po(purchase)
        self.assertEqual(purchase.picking_ids.state, "waiting")
        self._ship(sale, 3)
        transit_receipt = purchase.picking_ids
        self.assertEqual(transit_receipt.state, "done")
        self.assertEqual(
            transit_receipt.location_dest_id,
            self.warehouse_a.incoming_transit_location_id,
        )
        self.assertEqual(transit_receipt.move_lines.quantity_done, 3)
        physical_receipt = self._physical_receipts(purchase)
        self.assertEqual(physical_receipt.picking_type_id, self.warehouse_a.in_type_id)
        self.assertEqual(physical_receipt.state, "assigned")
        self.assertEqual(purchase.order_line.qty_received, 0)

    def test_physical_receipt_sets_received_quantity(self):
        purchase = self._create_purchase_order(self.partner_company_b)
        sale = self._approve_po(purchase)
        self._ship(sale, 3)
        physical_receipt = self._physical_receipts(purchase)
        physical_receipt.move_lines.quantity_done = 3
        physical_receipt.button_validate()
        self.assertEqual(physical_receipt.state, "done")
        self.assertEqual(purchase.order_line.qty_received, 3)

    def test_partial_delivery_backorders_transit_receipt(self):
        purchase = self._create_purchase_order(self.partner_company_b)
        sale = self._approve_po(purchase)
        self._ship(sale, 1)
        transit_receipt = purchase.picking_ids.filtered(lambda p: p.state == "done")
        self.assertEqual(transit_receipt.move_lines.quantity_done, 1)
        backorder = purchase.picking_ids - transit_receipt
        self.assertEqual(backorder.backorder_id, transit_receipt)
        self.assertEqual(backorder.move_lines.product_uom_qty, 2)
        self._ship(sale, 2)
        self.assertEqual(backorder.state, "done")
        self.assertEqual(backorder.move_lines.quantity_done, 2)
        self.assertEqual(transit_receipt.move_lines.quantity_done, 1)
        physical_receipt = self._physical_receipts(purchase)
        physical_receipt.move_lines.quantity_done = 3
        physical_receipt.button_validate()
        self.assertEqual(purchase.order_line.qty_received, 3)

    def test_delivery_without_backorder_cancels_transit_receipt_rest(self):
        purchase = self._create_purchase_order(self.partner_company_b)
        sale = self._approve_po(purchase)
        self._ship(sale, 1, backorder=False)
        transit_receipt = purchase.picking_ids
        self.assertEqual(transit_receipt.state, "done")
        self.assertEqual(sum(transit_receipt.move_lines.mapped("quantity_done")), 1)
        physical_receipt = self._physical_receipts(purchase)
        physical_receipt.move_lines.quantity_done = 1
        self._validate_without_backorder(physical_receipt)
        self.assertEqual(purchase.order_line.qty_received, 1)

    def test_serials_carried_to_transit_and_physical_receipts(self):
        purchase = self._create_purchase_order(
            self.partner_company_b, self.serial_product
        )
        sale = self._approve_po(purchase)
        self._ship_serials(sale, self.serials)
        transit_receipt = purchase.picking_ids
        self.assertEqual(transit_receipt.state, "done")
        self.assertEqual(
            transit_receipt.move_line_ids.lot_id.mapped("name"), ["111", "222", "333"]
        )
        physical_receipt = self._physical_receipts(purchase)
        self.assertEqual(physical_receipt.state, "assigned")
        self.assertEqual(
            physical_receipt.move_line_ids.lot_id, transit_receipt.move_line_ids.lot_id
        )

    def test_sync_never_touches_physical_receipts(self):
        self.warehouse_a.reception_steps = "two_steps"
        purchase = self._create_purchase_order(self.partner_company_b)
        sale = self._approve_po(purchase)
        self._ship(sale, 3)
        self.assertEqual(purchase.picking_ids.state, "done")
        physical_receipts = self._physical_receipts(purchase)
        self.assertEqual(physical_receipts.picking_type_id, self.warehouse_a.in_type_id)
        self.assertEqual(physical_receipts.state, "assigned")
        self.assertFalse(physical_receipts & purchase.picking_ids)
        self.assertFalse(physical_receipts.intercompany_picking_id)
