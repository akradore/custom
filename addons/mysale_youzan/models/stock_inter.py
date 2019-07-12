# -*- coding: utf-8 -*-
import datetime

from odoo import api, fields, models, _, tools
from odoo.addons.queue_job.job import job

from .. import constants
from ..yzsdk import YZClient

class StockInterPicking(models.Model):
    _inherit = 'stock.inter.picking'

    def _request_uri(self, req_uri, params):

        params['retail_source'] = constants.RETAIL_SOURCE
        debug = self.env['ir.config_parameter'].sudo().get_param(
            'mysale_youzan.mysale_youzan_push_message_is_debug_mode')

        yzclient = YZClient.get_default_client()
        result = yzclient.invoke(req_uri, '3.0.0', 'POST',
                                 params=params,
                                 debug=debug)
        return result['data']

    def get_wh_out_and_in_picking_type(self, from_wh, to_wh):
        # 总仓直配或回仓情况
        if 'ZC' in (from_wh.code, to_wh.code):
            if from_wh.code == 'ZC':
                out_ptype = from_wh.int_type_id
                in_ptype = to_wh.int_type_id

            else:
                out_ptype = from_wh.int_type_id.return_picking_type_id
                in_ptype = to_wh.int_type_id.return_picking_type_id

        else:  # 门店/电商仓之间调拨
            out_ptype = from_wh.int_type_id
            in_ptype = to_wh.int_type_id

        return out_ptype, in_ptype

    @api.model
    @job
    def action_youzan_allot_order_query_and_save(self, order_no):
        """ 复制有赞调拨单到odoo"""
        data = self._request_uri('youzan.retail.open.allotorder.get', {'allot_order_no': order_no})

        ResPartner = self.env['res.partner'].sudo()
        StockWarehouse = self.env['stock.warehouse'].sudo()
        Product = self.env['product.product'].sudo()
        self = self.sudo()

        stpo = self.search([('name', '=', order_no)])
        if not stpo:
            partner = ResPartner.create({
                'name': '%s至%s' % (data['from_warehouse_code'], data['to_warehouse_code']),
                # 'employee': True,
            })
            from_wh = StockWarehouse.search([('code', '=', data['from_warehouse_code'])])
            to_wh   = StockWarehouse.search([('code', '=', data['to_warehouse_code'])])
            from_wh.ensure_one()
            to_wh.ensure_one()

            sku_code_list = [i['sku_code'] for i in data['order_items']]
            products = Product.action_youzan_product_query_and_save(sku_code_list)
            products_dict = dict((p.default_code, p) for p in products)

            stpo_lines = []
            for item in data['order_items']:
                p = products_dict.get(item['sku_code'])
                stpo_lines.append((0, 0, {
                    'name': item['product_name'],
                    'product_id': p.id,
                    'qty': item['apply_num'],
                    'product_uom': p.uom_po_id.id,
                }))

            out_ptype, in_ptype = self.get_wh_out_and_in_picking_type(from_wh, to_wh)

            stpo = self.create({
                'name': order_no,
                'partner_id': partner.id,
                'out_picking_type': out_ptype.id,
                'in_picking_type': in_ptype.id,
                'order_date': data['created_time'] or datetime.datetime.now(), #计划调出日期
                'validity_date': data['created_time'] or datetime.datetime.now(),  #TODO　计划调入日期　可在调出时间基础上 + 1天时间
                'inter_type': set([from_wh.code, to_wh.code]) == set(['ZC', 'WDT']) and '1step' or '2step',
                'out_location': out_ptype.default_location_src_id.id,
                'in_location': in_ptype.default_location_dest_id.id,
                'notes': data['remark'],
                'inter_lines': stpo_lines,
            })

        else:
            for item in data['order_items']:
                line = stpo.inter_lines.search([('product_id.default_code', '=', item['sku_code'])])
                line.ensure_one()

                line.write({'qty': item['apply_num']})

        if stpo.state in ('draft',):
            stpo.action_progress()

        if stpo.state in ('progress',):
            stpo.action_inter_picking()

        return stpo

    @api.multi
    def action_youzan_allot_order_done(self):
        """ 确认有赞调拨单到货 """
        pass

    @api.model
    @job
    def action_youzan_distribution_order_query_and_save(self, order_no):
        """ 复制有赞配送单到odoo """
        data = self._request_uri('youzan.retail.open.distributionorder.get', {'biz_bill_no': order_no})

        ResPartner = self.env['res.partner'].sudo()
        StockWarehouse = self.env['stock.warehouse'].sudo()
        Product = self.env['product.product'].sudo()
        self = self.sudo()

        stpo = self.search([('name', '=', order_no)])
        if not stpo:
            partner = ResPartner.create({
                'name': '%s至%s'%(data['from_warehouse_code'], data['to_warehouse_code']),
                # 'employee': True,
            })
            from_wh = StockWarehouse.search([('code', '=', data['from_warehouse_code'])])
            to_wh = StockWarehouse.search([('code', '=', data['to_warehouse_code'])])
            from_wh.ensure_one()
            to_wh.ensure_one()

            sku_code_list = [i['sku_code'] for i in data['order_items']]
            products = Product.action_youzan_product_query_and_save(sku_code_list)
            products_dict = dict((p.default_code, p) for p in products)

            stpo_lines = []
            for item in data['order_items']:
                p = products_dict.get(item['sku_code'])
                stpo_lines.append((0, 0, {
                    'name': item['product_name'],
                    'product_id': p.id,
                    'qty': item['apply_num'],
                    'product_uom': p.uom_id.id,
                }))

            out_ptype, in_ptype = self.get_wh_out_and_in_picking_type(from_wh, to_wh)

            stpo = self.create({
                'name': order_no,
                'partner_id':partner.id,
                'out_picking_type': out_ptype.id,
                'in_picking_type': in_ptype.id,
                'order_date': data['distributed_out_time'] or datetime.datetime.now(), #　计划调出日期
                'validity_date': data['distributed_out_time']  or datetime.datetime.now(), # TODO　计划调入日期　可在调出时间基础上 + 1天时间
                'inter_type': set([from_wh.code, to_wh.code]) == set(['ZC', 'WDT']) and '1step' or '2step',
                'out_location': out_ptype.default_location_src_id.id,
                'in_location': in_ptype.default_location_dest_id.id,
                'notes': data['remark'],
                'inter_lines': stpo_lines,
            })

        else:
            for item in data['order_items']:
                line = stpo.inter_lines.search([('product_id.default_code', '=', item['sku_code'])])
                line.ensure_one()
                line.write({'qty': item['apply_num']})

        if stpo.state in ('draft',):
            stpo.action_progress()

        if stpo.state in ('progress',):
            stpo.action_inter_picking()

        return stpo




