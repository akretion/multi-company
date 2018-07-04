# -*- coding: utf-8 -*-
# © 2015 Akretion (http://www.akretion.com)
# Sébastien BEAU <sebastien.beau@akretion.com>
# Chafique Delli <chafique.delli@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from openerp import models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.onchange('state')
    def onchange_state(self):
        return self.env['sale.order']._compute_invoice_state()
