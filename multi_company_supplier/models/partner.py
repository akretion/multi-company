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

from openerp.osv.orm import Model
from openerp.osv import fields


class ResPartner(Model):
    _inherit = 'res.partner'

    _columns = {
        'partner_company_id': fields.many2one(
            'res.company', 'Company in OpenERP'
        ),
    }


class ResCompany(Model):
    _inherit = 'res.company'

    _columns = {
        'partner_ids': fields.one2many(
            'res.partner', 'partner_company_id', 'Partners in OpenERP'
        ),
    }
