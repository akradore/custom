# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re


from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class Picking(models.Model):
    _inherit = "stock.picking"

    source_order_type = fields.Selection([
        ('direct_order', '总部统配单'),
        ('apply_order', '要货配送单')],
        string='原单据类型',
        states={'done': [('readonly', True)]})


class QuantPackage(models.Model):
    """ Packages containing quants and/or other packages """
    _name = 'stock.quant.package'
    _inherit = "stock.quant.package"

    has_logistics = fields.Boolean('使用物流', compute='_compute_has_logistics', astore=True)

    logistics_company_id = fields.Many2one('mysale.base.logistics.company', '物流公司', ondelete='restrict',
                                           help="Vendor of this product")
    logistics_no = fields.Char(string='运单号', index=True)

    @api.onchange('logistics_company_id', 'logistics_no')
    def on_change_name(self):
        if self.logistics_company_id and self.logistics_no:
            self.name = '%s-%s' % (self.logistics_company_id.ref , self.logistics_no)

    @api.depends('logistics_company_id', 'logistics_no')
    def _compute_has_logistics(self):
        for package in self:
            if package.logistics_company_id and package.logistics_no:
                package.has_logistics = True
            else:
                package.has_logistics = False

    @api.one
    @api.constrains('logistics_company_id', 'logistics_no')
    def _check_logistics_regex_no(self):

        if self.logistics_company_id or self.logistics_no:

            if not self.logistics_company_id:
                raise ValidationError(_('请选择物流公司！'))

            if not self.logistics_no:
                raise ValidationError(_('请填写运单号！'))

            if not re.compile(self.logistics_company_id.logistics_regex_no).match(self.logistics_no):
                raise ValidationError(_('物流公司单号正则式与运单号不匹配！'))



