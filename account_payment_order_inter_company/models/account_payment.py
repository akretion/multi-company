# Copyright 2022 Akretion France (http://www.akretion.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

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
        vals = {
            "move_id": move.id,
            "partner_id": dest_invoice.commercial_partner_id.id,
            "company_id": dest_company.id,
            "name": dest_invoice.name,
        }
        if dest_invoice.state == "draft":
            vals["name"] = dest_invoice.ref
        else:
            vals["name"] = dest_invoice.name
        if self.payment_type == "outbound":
            vals["account_id"] = dest_invoice.partner_id.with_company(
                dest_company.id
            ).property_account_receivable_id.id
            vals["credit"] = payment_line.amount_currency
            vals["debit"] = 0.0
        else:
            vals["account_id"] = dest_invoice.partner_id.with_company(
                dest_company.id
            ).property_account_payable_id.id
            vals["credit"] = 0.0
            vals["debit"] = payment_line.amount_currency
        return vals

    def _create_move_lines(self, bank_journal, move, dest_company):
        move_lines = self._create_move_line_pending_account(
            bank_journal, move, dest_company
        )
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
            move_lines |= (
                self.env["account.move.line"]
                .with_context(check_move_validity=False)
                .create(move_line_vals)
            )
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
        return self.env["account.move"].with_company(dest_company.id).create(vals)

    def _reconcile_lines(self, move_lines):
        for line in move_lines.filtered(
            lambda line: line.account_internal_type in ["receivable", "payable"]
        ):
            lines_to_reconcile = line
            dest_invoice_line = self.env["account.move.line"].search(
                [
                    ("account_internal_type", "in", ["receivable", "payable"]),
                    ("move_name", "=", line.name),
                    ("company_id", "=", line.company_id.id),
                ],
                limit=1,
            )
            if not dest_invoice_line:
                # This is the case when the supplier invoice is not validated
                # In that case we have nothing to reconcile
                continue
            lines_to_reconcile |= dest_invoice_line
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
            move_lines = record._create_move_lines(bank_journal, move, dest_company)
            move.action_post()
            record._reconcile_lines(move_lines)
