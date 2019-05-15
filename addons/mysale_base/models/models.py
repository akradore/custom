# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    order_from = fields.Selection([
        ('default', 'DEFAULT'),
        ('yz_retail', 'YOUZAN Retail'),
        ('yz_mall', 'YOUZAN MALL'),
        ('taobao', 'TAOBAO'),
        ('jd', 'JINGDONG'),
        ], string='来自平台', readonly=True, copy=False, index=True, track_visibility='onchange', track_sequence=3, default='default')



class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    order_item_no = fields.Char(String='Order Item No', readonly=True, index=True)


