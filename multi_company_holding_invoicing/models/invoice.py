# -*- coding: utf-8 -*-
# © 2015 Akretion (http://www.akretion.com)
# Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import Warning as UserError
from openerp.addons.queue_job.job import job
import logging
_logger = logging.getLogger(__name__)



class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    holding_sale_ids = fields.One2many('sale.order', 'holding_invoice_id')
    holding_sale_count = fields.Integer(
        compute='_compute_holding_sale_count',
        string='# of Sales Order',
        compute_sudo=True)
    sale_count = fields.Integer(
        compute='_compute_sale_count',
        string='# of Sales Order',
        compute_sudo=True)
    child_invoice_ids = fields.One2many(
        'account.invoice', 'holding_invoice_id')
    child_invoice_count = fields.Integer(
        compute='_compute_child_invoice_count',
        string='# of Invoice',
        compute_sudo=True)
    holding_invoice_id = fields.Many2one('account.invoice', 'Holding Invoice')
    child_invoice_job_count = fields.Integer(
        compute='_compute_child_invoice_job_count',
        string='# of Child Invoice Jobs',
        compute_sudo=True)

    @api.multi
    def _compute_holding_sale_count(self):
        for inv in self:
            inv.holding_sale_count = len(inv.holding_sale_ids)

    @api.multi
    def _compute_sale_count(self):
        for inv in self:
            inv.sale_count = len(inv.sale_ids)

    @api.multi
    def _compute_child_invoice_count(self):
        for inv in self:
            inv.child_invoice_count = len(inv.sudo().child_invoice_ids)

    def _get_child_job(self):
        self.ensure_one()
        return self.env['queue.job'].sudo().search([
                ('record_ids', '=like', [self.id]),
                ("method_name", "=", "generate_child_invoice"),
                ('model_name', '=', "account.invoice"),
                ('state', '!=', 'done')
            ])

    @api.multi
    def open_child_job(self):
        jobs = self._get_child_job()
        action = self.env.ref("queue_job.action_queue_job").read()[0]
        action["domain"] = [("id", "in", jobs.ids)]
        return action

    @api.multi
    def _compute_child_invoice_job_count(self):
        for inv in self:
            inv.child_invoice_job_count = len(inv._get_child_job())

    @api.multi
    def invoice_validate(self):
        for invoice in self:
            if invoice.holding_sale_ids and invoice.user_id.id == self._uid:
                invoice = invoice.suspend_security()
            invoice.holding_sale_ids._set_invoice_state('invoiced')
            super(AccountInvoice, self).invoice_validate()
        return True

    @api.multi
    def unlink(self):
        # Give some extra right to the user who have generated
        # the holding invoice
        for invoice in self:
            if invoice.holding_sale_ids and invoice.user_id.id == self._uid:
                invoice = invoice.suspend_security()
            sale_obj = self.env['sale.order']
            sales = sale_obj.search([('holding_invoice_id', '=', invoice.id)])
            super(AccountInvoice, invoice).unlink()
            sales._set_invoice_state('invoiceable')
        return True

    @job(default_channel='root.heavyjob.childinvoice')
    def generate_child_invoice(self, company_id):
        self.ensure_one()
        domain = [
            ('company_id', '=', company_id),
            ('id', 'in', self.holding_sale_ids.ids)
        ]
        child_invoices = self.env['child.invoicing']._generate_invoice(domain)
        child_invoices.write({'holding_invoice_id': self.id})
        for child_invoice in child_invoices:
            child_invoice.signal_workflow('invoice_open')
        return True

    @api.multi
    def generate_child_invoice_job(self):
        # TODO add a group and check it
        for invoice in self.suspend_security():
            if invoice.child_invoice_ids:
                raise UserError(_(
                    'The child invoices have been already '
                    'generated for this invoice'))
            companies_ids = [
                    g["company_id"][1]
                    for g in self.env['sale.order'].read_group([
                        ('id', 'in', self.holding_sale_ids.ids),
                        ('company_id', '!=', self.company_id.id),
                    ], 'company_id', 'company_id')]
            for company_id in companies_ids:
                description = (
                    _('Generate child invoices for the company: %s') %
                    company_id)
                self.with_delay(description=description).generate_child_invoice(
                    company_id=company_id)
        return True


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    sale_line_ids = fields.Many2many(
        comodel_name='sale.order.line',
        relation='sale_order_line_invoice_rel',
        column1='invoice_id',
        column2='order_line_id')

    @api.multi
    def product_id_change(self, product, uom_id, qty=0, name='', type='out_invoice',
            partner_id=False, fposition_id=False, price_unit=False, currency_id=False,
            company_id=None):
        prod = self.env['product.product'].browse(product)
        if prod.is_royalty:
            type = {
                'in_invoice': 'out_invoice',
                'out_invoice': 'in_invoice',
                'in_refund': 'out_refund',
                'out_refund': 'in_refund',
                }[type]
        return super(AccountInvoiceLine, self).product_id_change(
            product, uom_id, qty=qty, name=name, type=type,
            partner_id=partner_id, fposition_id=fposition_id,
            price_unit=price_unit, currency_id=currency_id,
            company_id=company_id)
