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

from openerp.addons import decimal_precision as dp


class ProductSupplierinfo(Model):
    _inherit = 'product.supplierinfo'

    _columns = {
        'supplier_product_id': fields.many2one(
            'product.product', 'Supplier product'
        ),
        'supplier_product_code': fields.related(
            'supplier_product_id',
            'default_code',
            type="char",
            string="Supplier code",
        ),
        'supplier_company_id': fields.related(
            'name',
            'partner_company_id',
            type='many2one',
            relation='res.company'
        ),
    }


class ProductProduct(Model):
    _inherit = 'product.product'

    def _suppliers_usable_qty(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            quantity = 0.0
            for supplier in product.seller_ids:
                supplier_product = supplier.supplier_product_id
                if not supplier_product:
                    continue
                quantity += supplier_product.immediately_usable_qty
            res[product.id] = quantity
        return res

    _columns = {
        'customers_supplierinfo_ids': fields.one2many(
            'product.supplierinfo',
            'supplier_product_id',
            'Customers supplier info'
        ),
        'suppliers_immediately_usable_qty': fields.function(
            _suppliers_usable_qty,
            digits_compute=dp.get_precision('Product UoM'),
            type='float',
            string='Suppliers Immediately Usable',
            help="Quantity of products available for sale from our suppliers."),
    }

    def has_same_erp_supplier(self, cr, uid, ids, context=None):
        assert len(ids) == 1
        product = self.browse(cr, uid, ids[0], context=context)
        for supplierinfo in product.seller_ids:
            if supplierinfo.supplier_product_id:
                return True
        return False
