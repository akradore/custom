# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.addons.queue_job.job import job

from .. import constants
from ..yzsdk.yzclient import YZClient


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.model
    @job
    def action_youzan_purchase_order_query_and_save(self, order_no):
        """ 复制有赞采购单到odoo """

        PurchaseOrder = self.env['purchase.order'].sudo()
        ResPartner    = self.env['res.partner'].sudo()
        Product = self.env['product.product'].sudo()
        po = PurchaseOrder.search([('origin', '=', order_no)])
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
        supplier = ResPartner.action_youzan_supplier_query_and_save(supplier_code, supplier_name)

        order_lines = []
        sku_codes = [i['sku_code'] for i in data['order_items']]
        product_list = Product.action_youzan_product_query_and_save(sku_codes)
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

        po = PurchaseOrder.create({
            'name': '%s采购(%s)'%(data['warehouse_name'], data['purchase_order_no']),
            'origin': order_no,
            'date_order': fields.datetime.now(),
            # 'date_approve': data[],
            'partner_id': supplier.id,
            'state': 'draft',
            'notes': 'remark',
            'order_line': order_lines
        })

        PurchaseOrder.search([('origin', '=', order_no)]).action_youzan_purchase_order_done()

        return po



    @api.multi
    def action_youzan_purchase_order_done(self):
        """ 确认有赞采购单到货 """
        for po in self:
        # Confirm the purchase order.
            po.button_confirm()




