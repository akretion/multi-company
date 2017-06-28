# coding: utf-8
# © 2017 David BEAL @ Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import api, fields, models


class CompleteCompanyTransient(models.Model):
    _name = 'complete.company.transient'

    model_ids = fields.Many2many(
        comodel_name='ir.model', string="Models", required=True)
    data_ids = fields.Many2many(
        comodel_name='ir.model.data')
    company_id = fields.Many2one(comodel_name='res.company')

    @api.multi
    def apply(self):
        self.ensure_one()

    @api.model
    def weird_data(self):
        return ['', '__export__']

    @api.multi
    def reload(self):
        self.ensure_one()
        action = self.env.ref(
            'duplicate_config_data.action_complete_company_creation_act_window').read()[0]
        data = self.env['ir.model.data'].search([
            ('model', 'in', [x.model for x in self.model_ids]),
            ('module', 'not in', self.weird_data())])
        if data:
            self.data_ids = list(data._ids)
            print '      DATA', data
        action['res_id'] = self.id
        return action
