# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.queue_job.job import job

from .. import constants
from ..yzsdk import YZClient

class Inventory(models.Model):
    _inherits = "stock.inventory"

    def _request_uri(self, order_no, req_uri):
        params = {}
        params['biz_bill_no'] = order_no
        params['retail_source'] = constants.RETAIL_SOURCE

        debug = self.env['ir.config_parameter'].sudo().get_param(
            'mysale_youzan.mysale_youzan_push_message_is_debug_mode')

        yzclient = YZClient.get_default_client()
        result = yzclient.invoke(req_uri, '3.0.0', 'POST',
                                 params=params,
                                 debug=debug)
        return result['data']

    @api.model
    @job
    def action_youzan_stock_adjustment_query_and_save(self, order_no):
        """ 库存盘点单确认完成后更新入库 """
        data = self._request_uri(order_no, 'youzan.retail.open.stockcheckorder.get')
        if data['status'] != 'DONE': # 确认完成后入库
            return False

        ado = self.search([('name', '=', order_no)])
        if not ado:
            wh = self.env['stock.warehouse'].search([('code', '=', data['warehouse_code'])])
            wh.ensure_one()
            location_id = wh.int_type_id.default_location_dest_id.id

            inventory = self.env['stock.inventory'].create({
                'name': 'warehouse_code',
                'filter': 'partial',
                'location_id': location_id,
                'exhausted': True,  # should be set by an onchange
            })
            inventory.action_start()

            sku_code_list = [i['sku_code'] for i in data['order_items']]
            products = self.env['product.product'].action_youzan_product_query_and_save(sku_code_list)
            products_dict = dict((p.default_code, p) for p in products)

            inv_lines = []
            for item in data['order_items']:
                product = products_dict.get(item['sku_code'])
                inv_lines.append((0, 0, {
                    'inventory_id': inventory.id,
                    'product_id': product.id,
                    'product_uom_id': product.uom_id.id,
                    'product_qty': item['real_num'],
                    'location_id': location_id,
                }))

            self.env['stock.inventory.line'].create(inv_lines)
            inventory.action_validate()

        return ado

