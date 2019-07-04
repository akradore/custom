# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import ValidationError

from .. import constants
from ..yzsdk.yzclient import YZClient

class ProductCategory(models.Model):
    _inherits = "product.category"

    @api.model
    def action_youzan_productcategory_query_and_save(self, name):

        cat = self.search([('name', '=', name)])
        if not cat:
            cat = self.create([(0 , 0, {
                'name': name
            })])
        return cat


class ProductProduct(models.Model):
    _inherits = "product.product"

    @api.model
    def action_youzan_product_query_and_save(self, sku_code_list):

        saved_sku_codes = self.search(['|', ('default_code', 'not in', sku_code_list)]).mapped('default_code')
        unsaved_sku_codes = sku_code_list - saved_sku_codes
        if len(unsaved_sku_codes) > 100:
            raise ValidationError('获取sku数量超过100条, 请重写该方法！')

        params = {'page_no': 1, 'page_size': 100}
        params['sku_codes'] = unsaved_sku_codes
        params['retail_source'] = constants.RETAIL_SOURCE

        debug = self.env['ir.config_parameter'].sudo().get_param(
            'mysale_youzan.mysale_youzan_push_message_is_debug_mode')

        yzclient = YZClient.get_default_client()
        result = yzclient.invoke('youzan.retail.open.sku.query', '3.0.0', 'POST',
                                 params=params,
                                 debug=debug)
        data = result['data']

        product_list = []
        for sku in data.get('skus', []):
            cat = self.env['product.category'].action_youzan_productcategory_query_and_save(sku['category_name'])
            uom = self.env['uom.uom'].search([('name', '=', sku['unit']), (['category_id', 'in', (1,2)])]) # 类别：计数、计重
            if len(uom) != 1:
                raise ValidationError('未在系统找到有赞商品库存对应的单位：%s '%sku['unit'])

            product = self.create([{
                # 'product_tmpl_id': ( 0, 0, {
                #     'barcode': sku['sku_no'],
                # }),
                'name': sku['product_name'],
                'default_code': sku['sku_code'],
                'categ_id': cat,
                'barcode': sku['sku_no'],
                'uom_id': uom.id,
                'uom_po_id': uom.id,
                'list_price': sku['retail_price'],
                'standard_price': sku['avg_stock_in_cost'], # 按平均计价方式计算成本
                'type': 'consu'
            }])

            product_list.append(product)

        return product_list
