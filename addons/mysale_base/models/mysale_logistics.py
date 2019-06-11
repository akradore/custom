# -*- coding: utf-8 -*-

import base64
import os
import re

from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError

DEFAULT_LOGC_INDUSTRY_ID = 8

class LogisticsCompany(models.Model):
    _name = 'mysale.base.logistics.company'
    _description = '物流公司'
    _inherits = {'res.partner': 'partner_id'}
    _order = 'sequence, name'

    DEFAULT_INDUSTRY_ID = DEFAULT_LOGC_INDUSTRY_ID

    partner_id = fields.Many2one('res.partner', required=True, ondelete='restrict', auto_join=True,
                                 string='关联公司', help='物流公司关联')
    sequence = fields.Integer(help='排序值', default=10)

    industry_id = fields.Many2one(string='行业',related='partner_id.industry_id', default=lambda x: 8,
                                  domain=[('id', '=', 8)], help='仅运输行业')

    logistics_regex_no = fields.Char(string='物流单号正则式')
    logistics_default_val = fields.Char( string='参考物流单号')

    active_partner = fields.Boolean(related='partner_id.active', readonly=True, string="Partner is Active")
    active = fields.Boolean(default=True)

    @api.one
    @api.constrains('logistics_regex_no', 'logistics_default_val')
    def _check_logistics_regex_no(self):
        print('constrains', self.logistics_regex_no, self.logistics_default_val)
        if self.logistics_regex_no:

            if not self.logistics_default_val:
                raise ValidationError(_('请填写物流单号正则式匹配的参考物流单号，以便系统对正则式做校验。'))

            if not re.compile(self.logistics_regex_no).match(self.logistics_default_val):
                raise ValidationError(_('物流单号正则式与参考物流单号不匹配！'))

    @api.multi
    def toggle_active(self):
        for user in self:
            if not user.active and not user.partner_id.active:
                user.partner_id.toggle_active()
        super(LogisticsCompany, self).toggle_active()

