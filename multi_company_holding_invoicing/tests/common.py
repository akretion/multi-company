# -*- coding: utf-8 -*-
# © 2016 Akretion (http://www.akretion.com)
# Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo.tests.common import TransactionCase
from datetime import datetime

XML_COMPANY_A = 'multi_company_holding_invoicing.child_company_a'
XML_COMPANY_B = 'multi_company_holding_invoicing.child_company_b'
XML_COMPANY_HOLDING = 'base.main_company'
XML_AGREEMENT_1 = 'multi_company_holding_invoicing.agreement_market_1'
XML_AGREEMENT_2 = 'multi_company_holding_invoicing.agreement_market_2'
XML_PARTNER_ID = 'base.res_partner_2'


class CommonInvoicing(TransactionCase):

    def setUp(self):
        super(CommonInvoicing, self).setUp()
        # tests are called before register_hook
        # register suspend_security hook
        self.env['ir.rule']._register_hook()

        # Install COA for each company (Holding, Child A and Child B)
        self.wizard_obj = self.env['wizard.multi.charts.accounts']
        self.chart_template = self.env['account.chart.template'].create({
            'name': 'Test account_chart_update chart',
            'currency_id': self.env.ref('base.EUR').id,
            'code_digits': 6,
            'transfer_account_id': self.env.ref(
                'account_invoice_inter_company.pcg_X58').id,
        })
        wizard_child_comp_a = self.wizard_obj.create({
            'company_id': self.env.ref(
                'multi_company_holding_invoicing.child_company_a').id,
            'chart_template_id': self.chart_template.id,
            'code_digits': self.chart_template.code_digits,
            'transfer_account_id': self.env.ref(
                'account_invoice_inter_company.pcg_X58').id,
            'currency_id': self.chart_template.currency_id.id,
            'bank_account_code_prefix': '572',
            'cash_account_code_prefix': '570',
        })
        wizard_child_comp_a.onchange_chart_template_id()
        wizard_child_comp_a.execute()

        wizard_child_comp_b = self.wizard_obj.create({
            'company_id': self.env.ref(
                'multi_company_holding_invoicing.child_company_b').id,
            'chart_template_id': self.chart_template.id,
            'code_digits': self.chart_template.code_digits,
            'transfer_account_id': self.env.ref(
                'account_invoice_inter_company.pcg_X58').id,
            'currency_id': self.chart_template.currency_id.id,
            'bank_account_code_prefix': '572',
            'cash_account_code_prefix': '570',
        })
        wizard_child_comp_b.onchange_chart_template_id()
        wizard_child_comp_b.execute()

        wizard_holding_comp = self.wizard_obj.create({
            'company_id': self.env.ref(
                'base.main_company').id,
            'chart_template_id': self.chart_template.id,
            'code_digits': self.chart_template.code_digits,
            'transfer_account_id': self.env.ref(
                'account_invoice_inter_company.pcg_X58').id,
            'currency_id': self.chart_template.currency_id.id,
            'bank_account_code_prefix': '572',
            'cash_account_code_prefix': '570',
        })
        wizard_holding_comp.onchange_chart_template_id()
        wizard_holding_comp.execute()

    def _get_sales(self, xml_ids):
        sales = self.env['sale.order'].browse(False)
        for xml_id in xml_ids:
            sale = self.env.ref(
                'multi_company_holding_invoicing.sale_order_%s' % xml_id)
            sales |= sale
        return sales

    def _validate_and_deliver_sale(self, xml_ids):
        sales = self._get_sales(xml_ids)
        for sale in sales:
            sale.action_confirm()
            for picking in sale.picking_ids:
                picking.force_assign()
                picking.do_transfer()
        return sales

    def _set_partner(self, sale_xml_ids, partner_xml_id):
        partner = self.env.ref(partner_xml_id)
        sales = self._get_sales(sale_xml_ids)
        sales.write({
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
        })

    def _set_company(self, sale_xml_ids, company_xml_id):
        company = self.env.ref(company_xml_id)
        sales = self._get_sales(sale_xml_ids)
        sales.write({'company_id': company.id})

    def _set_agreement(self, sale_xml_ids, agreement_xml_id):
        agreement = self.env.ref(agreement_xml_id)
        sales = self._get_sales(sale_xml_ids)
        sales.write({'agreement_id': agreement.id})

    def _generate_holding_invoice(self, agreement_xml_id):
        invoice_date = datetime.today()
        wizard = self.env['wizard.holding.invoicing'].create({
            'agreement_id': self.env.ref(agreement_xml_id).id,
            'invoice_date': invoice_date,
        })
        res = wizard.create_invoice()
        invoices = self.env['account.invoice'].browse(res['domain'][0][2])
        return invoices

    def _generate_holding_invoice_from_sale(self, sales):
        invoice_date = datetime.today()
        wizard = self.env['sale.make.invoice'].with_context(
            active_ids=sales.ids).create({
                'invoice_date': invoice_date,
            })
        res = wizard.make_invoices()
        invoices = self.env['account.invoice'].browse(res['domain'][0][2])
        return invoices

    def _check_number_of_invoice(self, invoices, number):
        self.assertEqual(
            len(invoices), 1,
            msg="Only one invoice should have been created, %s created"
                % len(invoices))

    def _check_invoiced_sale_order(self, invoice, sales):
        self.assertEqual(
            sales,
            invoice.holding_sale_ids,
            msg="Expected sale order to be invoiced %s found %s"
                % (', '.join(sales.mapped('name')),
                   ', '.join(invoice.holding_sale_ids.mapped('name'))))

    def _check_expected_invoice_amount(self, invoice, expected_amount):
        self.assertEqual(
            expected_amount, invoice.amount_total,
            msg="The amount invoiced should be %s, found %s"
                % (expected_amount, invoice.amount_total))

    def _check_child_invoice(self, invoice):
        company2sale = {}
        for sale in invoice.holding_sale_ids:
            if not company2sale.get(sale.company_id.id):
                company2sale[sale.company_id.id] = sale
            else:
                company2sale[sale.company_id.id] |= sale
        for child in invoice.child_invoice_ids:
            expected_sales = company2sale.get(child.company_id.id)
            if expected_sales:
                expected_sales_name = ', '.join(expected_sales.mapped('name'))
            else:
                expected_sales_name = ''
            if child.sale_ids:
                found_sales_name = ', '.join(child.sale_ids.mapped('name'))
            else:
                found_sales_name = ''
            self.assertEqual(
                child.sale_ids, expected_sales,
                msg="The child invoice generated is not linked to the "
                    "expected sale order. Found %s, expected %s"
                    % (found_sales_name, expected_sales_name))

    def _check_child_invoice_partner(self, invoice):
        holding_partner = invoice.company_id.partner_id
        for child in invoice.child_invoice_ids:
            self.assertEqual(
                child.partner_id.id,
                holding_partner.id,
                msg="The partner invoiced is not correct excepted %s get %s"
                    % (holding_partner.name, child.partner_id.name))

    def _check_child_invoice_amount(self, invoice):
        discount = invoice.agreement_id.holding_discount
        expected_amount = invoice.amount_total * (1 - discount/100)
        computed_amount = 0
        for child in invoice.child_invoice_ids:
            computed_amount += child.amount_total
        self.assertAlmostEqual(
            expected_amount,
            computed_amount,
            msg="The total amoutn of child invoice is %s expected %s"
                % (computed_amount, expected_amount))

    def _check_sale_state(self, sales, expected_state):
        for sale in sales:
            self.assertEqual(
                sale.holding_invoice_state, expected_state,
                msg="Invoice state is '%s' indeed of '%s'"
                    % (sale.holding_invoice_state, expected_state))
