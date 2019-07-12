# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, SUPERUSER_ID, _

from .. import constants
from ..yzsdk.yzclient import YZClient

class Partner(models.Model):
    _inherit = "res.partner"

    @api.model
    def action_youzan_supplier_query_and_save(self, supplier_code, supplier_name):

        supplier = self.search(
            [('supplier', '=', True), '|', ('name', '=', supplier_name), ('ref', '=', supplier_code)])
        if not supplier:

            params = {'page_no': 1, 'page_size': 10}
            params['supplier_name'] = supplier_name
            params['retail_source'] = constants.RETAIL_SOURCE

            debug = self.env['ir.config_parameter'].sudo().get_param(
                'mysale_youzan.mysale_youzan_push_message_is_debug_mode')

            yzclient = YZClient.get_default_client()
            result = yzclient.invoke('youzan.retail.open.supplier.query', '3.0.0', 'POST',
                                     params=params,
                                     debug=debug)
            data = result['data']

            for sup in data.get('suppliers', []):
                supplier = self.create([{
                    'name': sup['supplier_name'],
                    'ref': sup['supplier_code'],
                    'supplier': True,
                    'phone': sup.get('phone'),
                    'email': sup.get('email'),
                    'fax': sup.get('fax'),
                    'comment': sup.get('remark'),
                    'notes': 'weixin：%s, QQ：%s' % (sup.get('wei_xin'), sup.get('qq')),
                }])

                supplier.write({
                    'child_ids': [(0, 0, {
                        'name': sup['contacts'],
                        'ref': sup.get('contacts_phone'),
                        'mobile': sup.get('contacts_phone'),
                        'type': 'contact',
                    })]
                })

        return supplier