# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class StockSynchron(models.Model):
    _name = 'mysale.stock.synchron'
    _order = 'id desc'
    _description = 'Synchronize stock with other platforms'

    name = fields.Char(
        '原单据号', default=lambda self: _('New'),
        copy=False, readonly=True, required=True,
        states={'done': [('readonly', True)]})

    source = fields.Char(
        '关联业务单据编号', index=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="关联业务单据编号（业务接收方传回的业务单号）")

    order_type_code = fields.Selection([
        ('distribution', '总仓配送单'),
        ('post_return', '配送回仓单'),
        ('stock_ckeck', '库存盘点单'),
        ('apply_stock', '门店叫货单'),
        ('stock_ajust', '库存调整单'),
        ('direct_post', '供应商直发')],
        string='单据类型',
        readonly=True)

    sync_type_code = fields.Selection([
        ('odoo2youzan', 'Odoo=>有赞的库存动作'),
        ('youzan2odoo', '有赞=>Odoo的库存动作'),
        ('odoo2wdt', 'Odoo=>旺店通的库存动作'),
        ('wdt2odoo', '旺店通=>Odoo的库存动作')],
        string='动作方向',
        readonly=True)

    owner_id = fields.Many2one('res.partner', '发起人', states={'done': [('readonly', True)]})

    synchrone_items = fields.One2many('mysale.stock.synchron.item', 'stock_synchron_id',
                                      string="库存同步", copy=True)

    from_warehouse_code = fields.Char(String='来源仓库编码', readonly=True, index=True)
    to_warehouse_code = fields.Char(String='目标仓库编码', readonly=True, index=True)

    from_warehouse_name = fields.Char(String='来源仓库名称', readonly=True)
    to_warehouse_name = fields.Char(String='目标仓库名称', readonly=True)

    state = fields.Selection([
        ('create', '待处理'),
        ('done', '已完成'),
        ('fail', '有错误'),
        ('cancel', '已取消'),
    ], string='状态', default="create")

    data_order = fields.Datetime('单据日期', index=True, default=fields.Datetime.now)
    date_done = fields.Datetime('完成时间')

    note = fields.Text('备注')
    refused_reason = fields.Text('拒绝/错误原因')

    @api.model
    def create(self, vals):
        if 'name' not in vals or vals['name'] == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('stock.scrap') or _('New')
        scrap = super(StockSynchron, self).create(vals)
        return scrap

    def unlink(self):
        if 'done' in self.mapped('state'):
            raise UserError(_('You cannot delete a synchrone which is done.'))
        return super(StockSynchron, self).unlink()


class StockSynchronItem(models.Model):
    _name = 'mysale.stock.synchron.item'
    _description = 'The details of Synchron Stock order'

    # product_id = fields.Many2one(
    #     'product.product', 'Product', domain=[('type', 'in', ['product', 'consu'])],
    #     required=True, states={'done': [('readonly', True)]})
    #
    # product_uom_id = fields.Many2one(
    #     'uom.uom', 'Unit of Measure',
    #     required=True, states={'done': [('readonly', True)]})

    name = fields.Char(String='商品名称', required=True)

    stock_synchron_id = fields.Many2one('mysale.stock.synchron', 'Stock Synchron', index=True,
                                        required=True, states={'done': [('readonly', True)]})

    supplier_code = fields.Char(String='供应商编码', index=True)
    sku_code = fields.Char(String='SKU编码', index=True, required=True)

    unit = fields.Char(String='周转单位', required=True)

    quantity = fields.Float(String='周转数量/申请数量', required=True)
    actual_out_num = fields.Float(String='实际出库数')
    actual_in_num = fields.Float(String='实际入库数量')

    with_tax_cost = fields.Float(String='含税成本单价（元）')
    with_tax_amount = fields.Float(String='含税总金额（含税成本单价*数量）（元）')
    with_tax_income = fields.Float(String='含税总收入（实付金额）')

    without_tax_amount = fields.Float(String='不含税总金额（不含税成本单价数量）')
    without_tax_cost = fields.Float(String='不含税成本单价（元）')

    checked_delivery_cost = fields.Float(String='不含税成本单价（元）')
    delivery_cost = fields.Float(String='不含税成本单价（元）')

    move_ids = fields.Many2many('stock.move', 'stock_move_synchrone_items', 'move_id', 'item_id', '库存移动明细',
                                help="对应的库存移动细节")

