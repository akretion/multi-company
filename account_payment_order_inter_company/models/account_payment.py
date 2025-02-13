# Copyright 2022 Akretion France (http://www.akretion.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class AccountPayment(models.Model):
    _inherit = "account.payment"

    auto_move_id = fields.Many2one(
        comodel_name="account.move", string="Inter company payment move"
    )

    def _create_move_line_pending_account(self, bank_journal, move, dest_company):
        vals = {
            "move_id": move.id,
            "company_id": dest_company.id,
        }
        if self.payment_type == "outbound":
            vals.update(
                {
                    "credit": 0.0,
                    "debit": self.amount,
                    "account_id": bank_journal.payment_debit_account_id.id,
                }
            )
        else:
            vals.update(
                {
                    "credit": self.amount,
                    "debit": 0.0,
                    "account_id": bank_journal.payment_credit_account_id.id,
                }
            )
        return (
            self.env["account.move.line"]
            .with_context(check_move_validity=False)
            .create(vals)
        )

    def _prepare_move_line_vals(self, payment_line, dest_invoice, move, dest_company):
        if dest_invoice:
            partner = dest_invoice.commercial_partner_id
            if dest_invoice.state == "draft":
                name = dest_invoice.ref
            else:
                name = dest_invoice.name
        else:
            partner = self.company_id.partner_id
            name = payment_line.communication
        vals = {
            "move_id": move.id,
            "partner_id": partner.id,
            "company_id": dest_company.id,
            "name": name,
        }
        if self.payment_type == "outbound":
            vals["account_id"] = partner.with_company(
                dest_company.id
            ).property_account_receivable_id.id
            if (
                float_compare(
                    payment_line.amount_currency,
                    0,
                    precision_rounding=payment_line.currency_id.rounding,
                )
                < 0
            ):
                vals["credit"] = 0.0
                vals["debit"] = -payment_line.amount_currency
            else:
                vals["credit"] = payment_line.amount_currency
                vals["debit"] = 0.0
        else:
            vals["account_id"] = partner.with_company(
                dest_company.id
            ).property_account_payable_id.id
            if (
                float_compare(
                    payment_line.amount_currency,
                    0,
                    precision_rounding=payment_line.currency_id.rounding,
                )
                < 0
            ):
                vals["credit"] = -payment_line.amount_currency
                vals["debit"] = 0.0
            else:
                vals["credit"] = 0.0
                vals["debit"] = payment_line.amount_currency

        return vals

    def _create_move_lines(self, bank_journal, move, dest_company):
        self._create_move_line_pending_account(bank_journal, move, dest_company)
        move_lines = []
        for payment_line in self.payment_line_ids:
            orig_invoice = payment_line.move_line_id.move_id
            if orig_invoice.auto_generated:
                dest_invoice = orig_invoice.auto_invoice_id
            else:
                dest_invoice = self.env["account.move"].search(
                    [
                        ("auto_invoice_id", "=", orig_invoice.id),
                        ("company_id", "=", dest_company.id),
                    ],
                    limit=1,
                )
            move_line_vals = self._prepare_move_line_vals(
                payment_line, dest_invoice, move, dest_company
            )
            move_line = (
                self.env["account.move.line"]
                .with_context(check_move_validity=False)
                .create(move_line_vals)
            )
            move_lines.append((move_line, dest_invoice))
        return move_lines

    def _prepare_move_vals(self, dest_company, bank_journal):
        vals = {
            "journal_id": bank_journal.id,
            "company_id": dest_company.id,
            "ref": self.payment_reference,
        }
        return vals

    def _create_move(self, dest_company, bank_journal):
        vals = self._prepare_move_vals(dest_company, bank_journal)
        move = self.env["account.move"].with_company(dest_company.id).create(vals)
        move_lines = self._create_move_lines(bank_journal, move, dest_company)
        move.action_post()
        self._reconcile_lines(move_lines)
        return move

    def _reconcile_lines(self, move_lines):
        for line, dest_invoice in move_lines:
            lines_to_reconcile = line
            dest_invoice_line = dest_invoice.line_ids.filtered(
                lambda l: l.account_internal_type in ["receivable", "payable"]
            )
            if not dest_invoice_line or dest_invoice.state == "draft":
                # This is the case when the supplier invoice is not validated
                # In that case we have nothing to reconcile
                continue
            lines_to_reconcile |= dest_invoice_line[0]
            lines_to_reconcile.reconcile()
        return True

    def reconcile_inter_company_invoices(self):
        for record in self:
            dest_company = self.env["res.company"].search(
                [("partner_id", "=", record.partner_id.id)], limit=1
            )
            if not dest_company:
                continue
            bank_journal = self.env["account.journal"].search(
                [
                    ("company_id", "=", dest_company.id),
                    ("type", "=", "bank"),
                    (
                        "bank_account_id.sanitized_acc_number",
                        "=",
                        record.partner_bank_id.sanitized_acc_number,
                    ),
                ],
                limit=1,
            )
            if not bank_journal:
                raise UserError(
                    _(
                        "No bank journal found for the bank account"
                        " %(account_number)s in the company %(company_name)s"
                    )
                    % dict(
                        account_number=record.partner_bank_id.sanitized_acc_number,
                        company_name=dest_company.name,
                    )
                )
            move = record._create_move(dest_company, bank_journal)
            record.auto_move_id = move.id

    def action_draft(self):
        result = super().action_draft()
        self.sudo().auto_move_id.button_draft()
        return result

    def action_cancel(self):
        result = super().action_cancel()
        self.sudo().auto_move_id.button_cancel()
        return result

    def unlink(self):
        moves = self.sudo().with_context(force_delete=True).auto_move_id
        moves.unlink()
        return super().unlink()
