# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _


class LogisticsCompany(models.Model):
    _inherit = 'mysale.base.logistics.company'

    ref_youzan = fields.Char(String='有赞参考编码', index=True)