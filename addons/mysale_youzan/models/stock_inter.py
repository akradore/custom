# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.addons.queue_job.job import job

from .. import constants
from ..yzsdk import YZClient

class StockInterPicking(models.Model):
    _inherits = 'stock.inter.picking'

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
    def action_youzan_allot_order_query_and_save(self, order_no):
        """ 复制有赞调拨单到odoo """
        data = self._request_uri(order_no, 'youzan.retail.open.allotorder.get')

        stpo = self.search([('name', '=', order_no)])
        if not stpo:
            partner = self.env['res.partner'].create({
                'name': '%s至%s' % (data['from_warehouse_code'], data['to_warehouse_code']),
                # 'employee': True,
            })
            from_wh = self.env['stock.warehouse'].search([('code', '=', data['from_warehouse_code'])])
            to_wh = self.env['stock.warehouse'].search([('code', '=', data['to_warehouse_code'])])
            from_wh.ensure_one()
            to_wh.ensure_one()

            sku_code_list = [i['sku_code'] for i in data['order_items']]
            products = self.env['product.product'].action_youzan_product_query_and_save(sku_code_list)
            products_dict = dict((p.default_code, p) for p in products)

            stpo_lines = []
            for item in data['order_items']:
                p = products_dict.get(item['sku_code'])
                stpo_lines.append((0, 0, {
                    'name': item['product_name'],
                    'product_id': p.id,
                    'qty': data['apply_num'],
                    'product_uom': p.uom_po_id.id,
                }))

            stpo = self.create({
                'name': data['allot_order_no'],
                'partner_id': partner.id,
                'out_picking_type': from_wh.int_type_id.id,
                'in_picking_type': to_wh.int_type_id.id,
                'order_date': data['created_time'],
                'inter_type': '2step',
                'out_location': from_wh.int_type_id.default_location_src_id.id,
                'in_location': to_wh.int_type_id.default_location_dest_id.id,
                'notes': data['remark'],
                'inter_lines': stpo_lines,
            })

        else:
            for item in data['order_items']:
                line = stpo.inter_lines.search([('product_id.default_code', '=', item['sku_code'])])
                line.ensure_one()

                line.write({'qty': item['apply_num']})

        return stpo

    @api.multi
    def action_youzan_allot_order_done(self):
        """ 确认有赞调拨单到货 """
        pass

    @api.model
    @job
    def action_youzan_distribution_order_query_and_save(self, order_no):
        """ 复制有赞配送单到odoo """
        data = self._request_uri(order_no, 'youzan.retail.open.distributionorder.get')

        stpo = self.search([('name', '=', order_no)])
        if not stpo:
            partner = self.env['res.partner'].create({
                'name': '%s至%s'%(data['from_warehouse_code'], data['to_warehouse_code']),
                # 'employee': True,
            })
            from_wh = self.env['stock.warehouse'].search([('code', '=', data['from_warehouse_code'])])
            to_wh = self.env['stock.warehouse'].search([('code', '=', data['to_warehouse_code'])])
            from_wh.ensure_one()
            to_wh.ensure_one()

            sku_code_list = [i['sku_code'] for i in data['order_items']]
            products = self.env['product.product'].action_youzan_product_query_and_save(sku_code_list)
            products_dict = dict((p.default_code, p) for p in products)

            stpo_lines = []
            for item in data['order_items']:
                p = products_dict.get(item['sku_code'])
                stpo_lines.append((0, 0, {
                    'name': item['product_name'],
                    'product_id': p.id,
                    'qty': data['apply_num'],
                    'product_uom': p.uom_id.id,
                }))

            stpo = self.create({
                'name': data['biz_bill_no'],
                'partner_id':partner.id,
                'out_picking_type': from_wh.int_type_id.id,
                'in_picking_type': to_wh.int_type_id.id,
                'order_date': data['distributed_out_time'],
                'inter_type': '2step',
                'out_location': from_wh.int_type_id.default_location_src_id.id,
                'in_location': to_wh.int_type_id.default_location_dest_id.id,
                'notes': data['remark'],
                'inter_lines': stpo_lines,
            })

        else:
            for item in data['order_items']:
                line = stpo.inter_lines.search([('product_id.default_code', '=', item['sku_code'])])
                line.ensure_one()
                line.write({'qty': item['apply_num']})

        return stpo


    @api.multi
    def action_youzan_distribution_order_done(self):
        """ 确认有赞采购单到货 """
        pass

