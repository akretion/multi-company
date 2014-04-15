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
{
    'name': 'multi_company_supplier',
    'version': '0.1',
    'category': 'Generic Modules/Others',
    'license': 'AGPL-3',
    'description': """This module permit to make a relation between a supplier
and a company in the same OpenERP database.

It permits to display the available stock of the supplier.""",
    'author': 'Akretion',
    'website': 'http://www.akretion.com/',
    'depends': ['base'],
    'data': [
        'views/partner.xml',
    ],
    'demo': [],
    'installable': True,
    'active': False,
}
