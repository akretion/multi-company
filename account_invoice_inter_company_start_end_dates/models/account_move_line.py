# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _prepare_account_move_line(self, dest_move, dest_company):
        vals = super()._prepare_account_move_line(dest_move, dest_company)
        vals.update(
            {
                "start_date": self.start_date,
                "end_date": self.end_date,
            }
        )
        return vals
