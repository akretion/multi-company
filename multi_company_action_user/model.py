# -*- coding: utf-8 -*-
################################################################################
#                                                                              #
#   multi_company_action_user for OpenERP                                      #
#   Copyright (C) 2013 Akretion Florian da Costa <florian.dacosta@akretion.com>#
#                                                                              #
#   This program is free software: you can redistribute it and/or modify       #
#   it under the terms of the GNU Affero General Public License as             #
#   published by the Free Software Foundation, either version 3 of the         #
#   License, or (at your option) any later version.                            #
#                                                                              #
#   This program is distributed in the hope that it will be useful,            #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of             #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the              #
#   GNU Affero General Public License for more details.                        #
#                                                                              #
#   You should have received a copy of the GNU Affero General Public License   #
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.      #
#                                                                              #
################################################################################

from openerp.osv import osv, orm
from tools.translate import _
from openerp import SUPERUSER_ID



def get_record_id_user(self, cr, uid, record_id, context=None):
    company_obj = self.pool['res.company']
    record_read = self.read(cr, SUPERUSER_ID, [record_id], ['company_id'])[0]
    if record_read['company_id']:
        comp_id = record_read['company_id'][0]
    else:
        raise orm.except_orm(_('Error !'),
                             _('No company found for the record_id %s on object %s' % (record_id, self._name)))
    res = company_obj.get_company_action_user(cr, uid, comp_id, context=context)
    return res

orm.Model.get_record_id_user = get_record_id_user

