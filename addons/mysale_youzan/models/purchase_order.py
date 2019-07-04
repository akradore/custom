# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models, SUPERUSER_ID, _

from .. import constants
from ..yzsdk.yzclient import YZClient


class PurchaseOrder(models.Model):
    _inherits = "purchase.order"

    @api.model
    def action_youzan_purchase_order_query_and_save(self, order_no):
        """ 复制有赞采购单到odoo """

        po = self.env['purchase.order'].search([('origin', '=', order_no)])
        if po:
            return po

        params = {}
        params['purchase_order_no'] = order_no
        params['retail_source'] = constants.RETAIL_SOURCE

        debug = self.env['ir.config_parameter'].sudo().get_param(
            'mysale_youzan.mysale_youzan_push_message_is_debug_mode')

        yzclient = YZClient.get_default_client()
        result = yzclient.invoke('youzan.retail.open.purchaseorder.get', '3.0.0', 'POST',
                                 params=params,
                                 debug=debug)
        data = result['data']

        supplier_code = data['supplier_code']
        supplier_name = data['supplier_name']
        supplier = self.env['res.partner'].action_youzan_supplier_query_and_update(supplier_code, supplier_name)

        order_lines = []
        sku_codes = [i['sku_code'] for i in data['order_items']]
        product_list = self.env['product.product'].action_youzan_product_query_and_save(sku_codes)
        product_dict = dict((p.default_code, p) for p in product_list)

        for line in data['order_items']:
            p = product_dict.get(line['sku_code'])
            order_lines.append((0, 0 , {
                'name': line['product_name'],
                'product_id': p.id,
                'product_qty': line['apply_num'],
                'product_uom': p.uom_po_id.id,
                'price_unit': line['without_tax_unit_cost'],
                'date_planned': data['estimated_arrival_time'],
            }))

        po = self.env['purchase.order'].create({
            'name': '%s采购(原单号：%s)'%(data['warehouse_name'], data['purchase_order_no']),
            'origin': data['purchase_order_no'],
            'date_order': fields.datetime.now(),
            # 'date_approve': data[],
            'partner_id': supplier.id,
            'state': 'draft',
            'notes': 'remark',
            'order_line': order_lines
        })

        return po



    @api.multi
    def action_youzan_purchase_order_done(self):
        """ 确认有赞采购单到货 """
        pass



