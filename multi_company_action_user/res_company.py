# -*- coding: utf-8 -*-
###############################################################################
#                                                                             #
#   multi_company_action_user for OpenERP                                     #
#   Copyright (C) 2013 Akretion Benoît GUILLOT <benoit.guillot@akretion.com>  #
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

from openerp.osv import osv, fields, orm
from tools.translate import _


class res_company(orm.Model):
    _inherit = "res.company"
    
    _columns = {
        'automatic_action_user_id': fields.many2one('res.users',
                                                    'Automatic actions user',
                                                    help='This user is the one '
                                                    'used for all the actions '
                                                    '(create(), write(),...) to '
                                                    'make on this company.'),
    }

    def get_company_action_user(self, cr, uid, company_id, context=None):
        user_id = self.read(cr, uid, company_id,
                            ['automatic_action_user_id'],
                            context=context)['automatic_action_user_id']
        if not user_id:
            raise osv.except_osv(_('Error !'),
                                 _('You need to define an automatic action user for the company !'))
        return user_id[0]
