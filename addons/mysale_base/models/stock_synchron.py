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
        '关联业务单号', index=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="如配送单关联要货单单号，出库单关联配货单号")

    result_no = fields.Char(
        '业务结果单号', index=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="业务接收方传回的业务单号")

    order_type_code = fields.Selection([
        ('stockin_order', '内部入库单'), # 内部仓库之间库存流转入库
        ('stockout_order', '内部出库单'), # 内部仓库之间库存流转出库
        # ('stock_ckeck', '库存盘点单'),
        # ('apply_stock', '门店要货单'),
        # ('apply_check', '要货单确认'),
        # ('distribution', '总仓配送单'),
        # ('stock_ajust', '库存调整单'),
        # ('direct_post', '供应商直发'),
        ],
        string='单据类型',
        states={'done': [('readonly', True)]})

    sync_type_code = fields.Selection([
        ('odoo2youzan', 'Odoo=>有赞'),
        ('youzan2odoo', '有赞=>Odoo'),
        ('odoo2wdt', 'Odoo=>旺店通'),
        ('wdt2odoo', '旺店通=>Odoo')],
        string='动作方向',
        states={'done': [('readonly', True)]})

    owner_id = fields.Many2one('res.partner', '发起人', states={'done': [('readonly', True)]})

    synchron_items = fields.One2many('mysale.stock.synchron.item', 'stock_synchron_id',
                                      string="库存同步", copy=True)

    from_warehouse_code = fields.Char(string='来源仓库编码', index=True,
                                      states={'done': [('readonly', True)]})
    to_warehouse_code = fields.Char(string='目标仓库编码', index=True,
                                    states={'done': [('readonly', True)]})

    from_warehouse_name = fields.Char(string='来源仓库名称', states={'done': [('readonly', True)]})
    to_warehouse_name = fields.Char(string='目标仓库名称', states={'done': [('readonly', True)]})

    state = fields.Selection([
        ('create', '待处理'),
        ('check', '已审核'),
        ('partially_done', '部分完成'),
        ('done', '已完成'),
        ('fail', '有错误'),
        ('cancel', '已取消'),
    ], string='状态', compute='_compute_state', default="create", states={'done': [('readonly', True)]})

    data_order = fields.Datetime('单据日期', index=True, default=fields.Datetime.now, readonly=True)
    date_done  = fields.Datetime('完成时间')

    package_id = fields.Many2one('stock.quant.package', '库存同步记录')

    note = fields.Text('备注')
    refused_reason = fields.Text('拒绝/错误原因', states={'done': [('readonly', True)]})

    @api.model
    def create(self, vals):
        if 'name' not in vals or vals['name'] == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('stock.scrap') or _('New')
        scrap = super(StockSynchron, self).create(vals)
        return scrap

    def unlink(self):
        if 'done' in self.mapped('state'):
            raise UserError(_('You cannot delete a synchron which is done.'))
        return super(StockSynchron, self).unlink()

    @api.depends('from_warehouse_code')
    @api.returns('stock.warehouse')
    @api.one
    def from_warehouse(self):
        domain = [('code', '=', self.from_warehouse_code)]
        wh = self.env['stock.warehouse'].search(domain, limit=1)
        return wh

    @api.depends('to_warehouse_code')
    @api.returns('stock.warehouse')
    @api.one
    def to_warehouse(self):
        domain = [('code', '=', self.to_warehouse_code)]
        wh = self.env['stock.warehouse'].search(domain, limit=1)
        return wh

    @api.depends('synchron_items.state', 'synchron_items.stock_synchron_id')
    @api.one
    def _compute_state(self):
        if not self.synchron_items:
            self.state = 'create'
        elif all(item.state in ['create', 'fail', 'cancel', 'check' ] for item in self.synchron_items):
            self.state = self.synchron_items[0].state
        elif all(item.state in ['cancel', 'done'] for item in self.synchron_items):
            self.state = 'done'
        else:
            self.state = 'partially_done'


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

    name = fields.Char(string='商品名称', required=True)

    stock_synchron_id = fields.Many2one('mysale.stock.synchron', 'Stock Synchron', index=True,
                                        required=True, states={'done': [('readonly', True)]})

    supplier_code = fields.Char(string='供应商编码', index=True)
    sku_code = fields.Char(string='SKU编码', index=True, required=True)
    product_id = fields.Many2one('product.product', '商品', domain=[('type', 'in', ['product', 'consu'])],
                                 states={'done': [('readonly', True)]})

    unit = fields.Char(string='周转单位', required=True)
    product_uom_id = fields.Many2one('uom.uom', '商品单位', states={'done': [('readonly', True)]})

    quantity = fields.Float(string='周转数量/申请数量', default=0, required=True)
    pre_out_num = fields.Float(string='预发数量', default=0)
    actual_out_num = fields.Float(string='实际出库数', default=0)
    actual_in_num = fields.Float(string='实际入库数量', default=0)

    with_tax_cost = fields.Float(string='含税成本单价（元）', default=0)
    with_tax_amount = fields.Float(string='含税总金额（含税成本单价*数量）（元）', default=0)
    with_tax_income = fields.Float(string='含税总收入（实付金额）', default=0)

    without_tax_amount = fields.Float(string='不含税总金额（不含税成本单价数量）', default=0)
    without_tax_cost = fields.Float(string='不含税成本单价（元）', default=0)

    checked_delivery_cost = fields.Float(string='审核配送价', default=0)
    delivery_cost = fields.Float(string='配送价', default=0)

    move_ids = fields.Many2many('stock.move', 'stock_move_synchrone_items', 'move_id', 'item_id', '库存移动明细',
                                help="对应的库存移动细节")

    order_type_code = fields.Selection(related='stock_synchron_id.order_type_code', string='单据类型', readonly=True)

    sync_type_code = fields.Selection(related='stock_synchron_id.sync_type_code', string='动作方向', readonly=True)

    state = fields.Selection([
        ('create', '待处理'),
        ('check', '已审核'),
        ('partially_done', '部分完成'),
        ('done', '已完成'),
        ('fail', '有错误'),
        ('cancel', '已取消'),
    ], string='状态', default="create", states={'done': [('readonly', True)]})

    # @api.depends('synchron_items.state', 'synchron_items.stock_synchron_id')
    # @api.one
    # def _compute_state(self):
    #     if not self.synchron_items:
    #         self.state = 'create'
    #     elif all(item.state in ['create', 'fail', 'cancel', 'check'] for item in self.synchron_items):
    #         self.state = self.synchron_items[0].state
    #     elif all(item.state in ['cancel', 'done'] for item in self.synchron_items):
    #         self.state = 'done'
    #     else:
    #         self.state = 'partially_done'