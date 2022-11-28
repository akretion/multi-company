# Copyright 2013-Today Odoo SA
# Copyright 2016-2019 Chafique DELLI @ Akretion
# Copyright 2018-2019 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    auto_purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Source Purchase Order",
        readonly=True,
        copy=False,
    )

    _sql_constraints = [
        (
            "auto_purchase_order_id_uniq",
            "unique (auto_purchase_order_id)",
            "The auto_purchase_order_id must be unique !",
        )
    ]

    def action_confirm(self):
        for order in self.filtered("auto_purchase_order_id"):
            for line in order.order_line.sudo():
                if line.auto_purchase_line_id:
                    line.auto_purchase_line_id.price_unit = line.price_unit
        return super().action_confirm()

    def unlink(self):
        for record in self:
            if not self._context.get("force_delete") and record.auto_purchase_order_id:
                raise UserError(
                    _("You can not delete a intercompany sale, please cancel it")
                )
        return super().unlink()


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    auto_purchase_line_id = fields.Many2one(
        comodel_name="purchase.order.line",
        string="Source Purchase Order Line",
        readonly=True,
        copy=False,
    )
