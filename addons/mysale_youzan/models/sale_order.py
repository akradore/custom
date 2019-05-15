# -*- coding: utf-8 -*-

from odoo import models, fields, api

from ..yzsdk import YZClient

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ex_order_from = fields.Selection([
    #     ('default', 'DEFAULT'),
    #     ('yz_retail', 'YOUZAN Retail'),
    #     ('taobao', 'TAOBAO'),
    #     ('jd', 'JINGDONG'),
    #     ('yz_mall', 'YOUZAN MALL'),
    #     ], string='来自平台', readonly=True, copy=False, index=True, track_visibility='onchange', track_sequence=3, default='default')

    def click_yz_retial_order_update(self):

        params = {
            'status': 'NO_NEED_TO_DELIVER',
            'create_time_start': '2019-04-10 00:00:00',
            'create_time_end':'2019-05-10 00:00:00',
            'retail_source':'odoo',
        }

        yzclient = YZClient.get_default_client()
        resp_params = yzclient.invoke('youzan.retail.open.deliveryorder.query', '3.0.0', 'POST', params=params, files=[])
        for res in resp_params:

            result = self.env['sale.order'].search([
                ('origin', '=', res['delivery_order_no']),
                ('is_mysale_youzan', '=', True)
            ])
            obj = result.fetchone()
            if not obj:
                self.env.cr
                # TODO

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # order_item_no = fields.Char(String='Youzan Retail OrderItemNo', readonly=True, index=True)

