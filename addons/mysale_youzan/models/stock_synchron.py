# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.queue_job.job import job

from .. import constants
from ..yzsdk import YZClient


class StockSynchron(models.Model):
    _inherit = 'mysale.stock.synchron'

    @api.multi
    @job
    def action_distributionorder_create(self):
        """ 同步总部统配门店配货单至有赞 """
        self.ensure_one()

        data = {
            'biz_bill_no': self.name,
            'from_warehouse_code': self.from_warehouse_code,
            'to_warehouse_code': self.to_warehouse_code,
            'remark': self.note or '',
            'retail_source': constants.RETAIL_SOURCE,
            'kdt_id': constants.YOUZAN_AUTHORITY_ID,
            'order_items': []
        }

        for item in self.synchrone_items:
            data['order_items'].append({
                'sku_code': item.sku_code,
                'apply_num': '%.3f' % item.quantity,
                'delivery_price_str': '%.4f' % item.delivery_cost  # TODO 配送价加盟店要货必填
            })

        yzclient = YZClient.get_default_client()
        access_token = self.env['res.config.settings'].get_youzan_access_token()
        debug = self.env['ir.config_parameter'].sudo().get_param(
            'mysale_youzan.mysale_youzan_push_message_is_debug_mode')
        try:
            result = yzclient.invoke('youzan.retail.open.distributionorder.create', '3.0.0', 'POST',
                                     params={'request': data},
                                     files=[],
                                     access_token=access_token,
                                     debug=debug)

        except Exception as exc:
            self.write({
                'refused_reason': str(exc),
                'state': 'fail'
            })
            raise exc

        else:
            self.write({
                'done_data': fields.datetime.now(),
                'source': result['data'],
                'state': 'done'
            })

        return True


class StockSynchronItem(models.Model):
    _inherit = 'mysale.stock.synchron.item'
