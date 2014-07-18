# -*- coding: utf-8 -*-
###############################################################################
#                                                                             #
#   multi_company_supplier for OpenERP                                        #
#   Copyright (C) 2014 Akretion Arthur Vuillard <arthur.vuillard@akretion.com>#
#                                                                             #
#   This program is free software: you can redistribute it and/or modify      #
#   it under the terms of the GNU Affero General Public License as            #
#   published by the Free Software Foundation, either version 3 of the        #
#   License, or (at your option) any later version.                           #
#                                                                             #
#   This program is distributed in the hope that it will be useful,           #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of            #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the             #
#   GNU Affero General Public License for more details.                       #
#                                                                             #
#   You should have received a copy of the GNU Affero General Public License  #
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.     #
#                                                                             #
###############################################################################

from openerp import SUPERUSER_ID
from openerp.osv.orm import Model
from openerp.osv import fields


class ResPartner(Model):
    _inherit = 'res.partner'

    _columns = {
        'partner_company_id': fields.many2one(
            'res.company', 'Company in OpenERP'
        ),
    }

    def find_company_partner_id(self, cr, uid, company_id, owner_company_id,
                                context=None):
        partner_ids = self.search(
            cr, SUPERUSER_ID,
            [
                ('partner_company_id', '=', company_id),
                ('company_id', '=', owner_company_id),
                ('active', '=', True),
            ],
            context=context
        )
        if partner_ids:
            return partner_ids[0]
        return None

    def find_company_customer_id(self, cr, uid, company_id, owner_company_id,
                                 context=None):
        partner_ids = self.search(
            cr, SUPERUSER_ID,
            [
                ('partner_company_id', '=', company_id),
                ('company_id', '=', owner_company_id),
                ('active', '=', True),
                ('customer', '=', True),
            ],
            context=context
        )
        if partner_ids:
            return partner_ids[0]
        return None


class ResCompany(Model):
    _inherit = 'res.company'

    _columns = {
        'partner_ids': fields.one2many(
            'res.partner', 'partner_company_id', 'Partners in OpenERP'
        ),
    }
