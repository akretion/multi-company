# Copyright 2026 Tecnativa - Carlos Lopez

from odoo import Command, models


class ReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    def _create_return(self):
        new_picking = super()._create_return()
        if self._should_create_intercompany_return():
            purchase_return_wizard = self._create_intercompany_return_wizard(
                new_picking
            )
            purchase_return_wizard.with_context(
                skip_create_returns=True
            )._create_return()
        return new_picking

    def _should_create_intercompany_return(self):
        return self.picking_id._is_intercompany_delivery() and not self.env.context.get(
            "skip_create_returns", False
        )

    def _create_intercompany_return_wizard(self, sale_return_picking):
        """Create the counterpart purchase return wizard.

        ``sale_return_picking`` is not used here, but it is passed for the
        overrides (e.g. purchase_sale_stock_inter_company_mrp) that need it.
        """
        purchase_return_wizard = self._new_intercompany_return_wizard()
        # stock_picking_return_lot compatibility
        if "lot_id" in purchase_return_wizard.product_return_moves._fields:
            exclude_moves = purchase_return_wizard.product_return_moves.filtered(
                lambda line: line.lot_id not in self.product_return_moves.lot_id
            )
        else:
            exclude_moves = purchase_return_wizard.product_return_moves.filtered(
                lambda line: line.product_id not in self.product_return_moves.product_id
            )
        purchase_return_wizard.product_return_moves = [
            Command.unlink(prm.id) for prm in exclude_moves
        ]
        for wizard_line in self.product_return_moves:
            dest_line = purchase_return_wizard.product_return_moves.filtered(
                lambda line, wizard_line=wizard_line: line.product_id
                == wizard_line.product_id
            )
            # stock_picking_return_lot compatibility
            if "lot_id" in wizard_line._fields:
                dest_line = dest_line.filtered(
                    lambda x, wizard_line=wizard_line: x.lot_id == wizard_line.lot_id
                )
            dest_line.write({"quantity": wizard_line.quantity})
        return purchase_return_wizard

    def _new_intercompany_return_wizard(self):
        intercompany_picking = self.picking_id.intercompany_picking_id
        purchase_company = intercompany_picking.sudo().company_id
        intercompany_user = purchase_company.intercompany_sale_user_id
        intercompany_picking = intercompany_picking.with_user(intercompany_user)
        vals = {"picking_id": intercompany_picking.id}
        return (
            self.env["stock.return.picking"]
            .with_context(active_id=intercompany_picking.id)
            .with_user(intercompany_user)
            .with_company(purchase_company)
            .create(vals)
        )
