# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import ValidationError

from .. import constants
from ..yzsdk.yzclient import YZClient

class ProductCategory(models.Model):
    _inherit = "product.category"

    @api.model
    def action_youzan_productcategory_query_and_save(self, name):

        cat = self.search([('name', '=', name)])
        if not cat and name:
            cat = self.create({
                'name': name
            })
        return cat


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def action_youzan_product_query_and_save(self, sku_code_list):

        saved_sku_codes = self.search([('default_code', 'in', sku_code_list)]).mapped('default_code')
        unsaved_sku_codes = list(set(sku_code_list) - set(saved_sku_codes))

        page_no = 0
        page_size = 20
        count = len(unsaved_sku_codes)
        while count > 0 and page_no * page_size <= count:

            params = {'page_no': page_no + 1, 'page_size': page_size}
            params['sku_codes'] = unsaved_sku_codes[page_no * page_size: (page_no + 1) * page_size]
            params['retail_source'] = constants.RETAIL_SOURCE

            page_no += 1
            debug = self.env['ir.config_parameter'].sudo().get_param(
                'mysale_youzan.mysale_youzan_push_message_is_debug_mode')

            yzclient = YZClient.get_default_client()
            result = yzclient.invoke('youzan.retail.open.sku.query', '3.0.0', 'POST',
                                     params=params,
                                     debug=debug)
            data = result['data']

            for sku in data.get('skus', []):
                cat = sku['category_name'] and self.env['product.category'].action_youzan_productcategory_query_and_save(sku['category_name'])
                uom = self.env['uom.uom'].with_context({'lang': 'zh_CN'})\
                    .search([('name', '=', sku['unit']), ('category_id', 'in', (1,2))]) # 类别：1计数、2计重
                if len(uom) != 1:
                    raise ValidationError('未在系统找到有赞商品库存对应的单位：%s '% sku['unit'])

                self.create([{
                    'name': sku['product_name'],
                    'default_code': sku['sku_code'],
                    'categ_id': cat and cat.id or self.env.ref('product.product_category_1').id,
                    'barcode': sku['sku_no'],
                    'uom_id': uom.id,
                    'uom_po_id': uom.id,
                    'list_price': sku['retail_price'],
                    'standard_price': sku['avg_stock_in_cost'], # 按移动平均计价方式计算成本
                    'type': 'product', #  storable
                }])

        return self.search([('default_code', 'in', sku_code_list)])
