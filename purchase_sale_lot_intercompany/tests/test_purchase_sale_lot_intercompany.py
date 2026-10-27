# Copyright 2023 Akretion (https://www.akretion.com).
# @author Kévin Roche <kevin.roche@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.purchase_sale_inter_company.tests.common import (
    TestPurchaseSaleInterCompanyCommon,
)


class TestPurchaseSaleLotIntercompany(TestPurchaseSaleInterCompanyCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_company_b.groups_id |= cls.env.ref("stock.group_stock_user")
        cls.lot_test = cls.env["stock.production.lot"].create(
            {
                "name": "lot_test",
                "product_id": cls.product.id,
                "company_id": cls.warehouse_a.company_id.id,
            }
        )
        cls.purchase_company_a.order_line[0].lot_id = cls.lot_test

    def test_with_propagated_serial_number(self):
        self.company_b.propagated_serial_number = True
        sale = self._approve_po(self.purchase_company_a)
        self.assertEqual(sale.order_line[0].lot_id.name, "lot_test")
        self.assertEqual(sale.order_line[0].lot_id.company_id, self.company_b)

    def test_without_propagated_serial_number(self):
        sale = self._approve_po(self.purchase_company_a)
        self.assertTrue(sale.order_line)
        self.assertFalse(sale.order_line[0].lot_id)
