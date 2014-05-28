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

    def _get_validity(self, cr, uid, ids, field_name, args, context=None):
        result = {}
        invalid_ids = self.search(cr, uid, [
            ['name.partner_company_id', '!=', False],
            ['supplier_product_id', '=', False],
            ['id', 'in', ids],
            ], context=context)
        for supplier_id in ids:
            result[supplier_id] = supplier_id in invalid_ids
        return result

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
        'invalid_supplier_info': fields.function(
            _get_validity,
            string='Invalid Supplier Info',
            type='boolean',
            store={
                'product.supplierinfo': (
                    lambda self, cr, uid, ids, c={}: ids,
                    ['supplier_product_id', 'name'],
                    10),
                },
            ),
    }


class ProductProduct(Model):
    _inherit = 'product.product'

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        change = True
        for arg in args:
            if isinstance(arg, str):
                continue
            if arg[0] == 'company_id':
                change = False
                break
        if change:
            user = self.pool.get('res.users').read(cr, uid, uid, context=context)
            args.append(('company_id', '=', user['company_id'][0]))
        return super(ProductProduct, self).search(cr, uid, args, offset, limit, order, context)

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

    def _standard_price_compute(self, cr, uid, ids, name, arg, context=None):
        pricelist_obj = self.pool.get('product.pricelist')
        partner_obj = self.pool.get('res.partner')
        user_obj = self.pool.get('res.users')

        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            for supplier in product.seller_ids:
                supplier_product = supplier.supplier_product_id
                if not supplier_product:
                    continue
                user = user_obj.browse(cr, uid, uid, context=context)
                partner_id = partner_obj.find_company_partner_id(
                    cr, uid,
                    user.company_id.id,
                    supplier_product.company_id.id,
                    context=context
                )
                if not partner_id:
                    res[product.id] = supplier_product.list_price
                    break
                partner = partner_obj.browse(
                    cr, uid, partner_id, context=context
                )
                pricelist_id = partner.property_product_pricelist.id
                if pricelist_id:
                    pricelist_res = pricelist_obj.price_get(
                        cr, uid,
                        [pricelist_id],
                        supplier_product.id,
                        1,
                        partner=partner.id,
                        context=context
                    )
                    res[product.id] = pricelist_res[pricelist_id]
                else:
                    res[product.id] = supplier_product.list_price
                break
            if product.id not in res:
                res[product.id] = product.manual_cost_price
        return res

    def _has_same_erp_supplier(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = False
            for supplierinfo in product.seller_ids:
                if supplierinfo.name.partner_company_id:
                    res[product.id] = True
                    break
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
            help="Quantity of products available for sale from our suppliers."
        ),
        'manual_cost_price': fields.float(
            'Cost',
            digits_compute=dp.get_precision('Product Price'),
            help="Cost price of the product used for standard stock valuation "
                 "in accounting and used as a base price on purchase orders.",
            groups="base.group_user"
        ),
        'standard_price': fields.function(
            _standard_price_compute,
            type='float',
            string='Cost',
            groups="base.group_user"
        ),
        'has_same_erp_supplier': fields.function(
            _has_same_erp_supplier,
            type="boolean",
        ),
    }
