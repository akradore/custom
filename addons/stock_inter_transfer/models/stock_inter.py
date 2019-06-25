# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from datetime import timedelta
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_round, float_is_zero
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
import logging

_logger = logging.getLogger(__name__)


class StockInterPicking(models.Model):
    _name = 'stock.inter.picking'
    _description = u"仓库调拨单"

    @api.depends('inter_lines.out_picking_ids', 'inter_lines.in_picking_ids')
    def _compute_inter_picking(self):
        for order in self:
            picking_ids = self.env['stock.picking']
            picking_ids |= order.inter_lines.mapped('out_picking_ids')
            picking_ids |= order.inter_lines.mapped('in_picking_ids')
            order.inter_picking_ids = picking_ids
            order.inter_picking_count = len(picking_ids)

    partner_id = fields.Many2one('res.partner','业务伙伴')
    name = fields.Char(string=u'单号', required=False, copy=False, readonly=True,
                       index=True, default=lambda self: 'New')
    inter_type2 = fields.Many2one('stock.inter.type', string=u'调拨区分', readonly=True, copy=False, required=False,
                                  states={'draft': [('readonly', False)]})
    order_date = fields.Datetime(string=u'计划调出日期', required=False, readonly=True, index=True,
                                 states={'draft': [('readonly', False)]}, copy=False,
                                 default=fields.Datetime.now)
    validity_date = fields.Datetime(string=u'计划调入日期', readonly=True, required=False,
                                    states={'draft': [('readonly', False)]},
                                    default=fields.Datetime.now)
    state = fields.Selection([
        ('draft', u'草稿'),
        ('progress', u'调拨中'),
        ('done', u'完成'),
        ('cancel', u'取消'),
    ], string=u'状态', readonly=True, copy=False, index=True, default='draft')
    inter_type = fields.Selection([
        ('1step', u'一步调拨'),
        ('2step', u'两步调拨'),
    ], string=u'调拨类型', readonly=True, copy=True, states={'draft': [('readonly', False)]}, default='1step')
    out_location = fields.Many2one('stock.location', string=u'调出库', readonly=True, copy=False,
                                   states={'draft': [('readonly', False)]})
    in_location = fields.Many2one('stock.location', string=u'调入库', readonly=True, copy=False,
                                  states={'draft': [('readonly', False)]})
    out_picking_type = fields.Many2one('stock.picking.type', string=u'调出类型', readonly=True, copy=False,
                                       states={'draft': [('readonly', False)]})
    in_picking_type = fields.Many2one('stock.picking.type', string=u'调入类型', readonly=True, copy=False,
                                      states={'draft': [('readonly', False)]})
    user_id = fields.Many2one('res.users', string=u'责任人', readonly=True, copy=True,
                              states={'draft': [('readonly', False)]}, default=lambda self: self.env.user)

    inter_lines = fields.One2many('stock.inter.line', 'order_id', string=u'调拨明细',
                                  states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True)
    inter_picking_ids = fields.Many2many('stock.picking', compute="_compute_inter_picking", string=u'仓库调拨单', copy=False,
                                         store=True)
    inter_picking_count = fields.Integer(compute="_compute_inter_picking", string=u'调拨单数', copy=False, default=0,
                                         store=True)
    notes = fields.Char(string=u'源单据', readonly=True, states={'draft': [('readonly', False)]})
    company_id = fields.Many2one('res.company', u'公司',
                                 default=lambda self: self.env['res.company']._company_default_get('stock.picking'),
                                 states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True)
    active = fields.Boolean(default=True, help="Set active to false to hide this order.")

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('stock.inter.picking') or _('New')
        result = super(StockInterPicking, self).create(vals)
        return result

    @api.onchange('inter_type2')
    def _inter_type2_change(self):
        if self.inter_type2:
            self.inter_type = self.inter_type2.inter_type or self.inter_type
            self.out_location = self.inter_type2.out_location or self.out_location
            self.in_location = self.inter_type2.in_location or self.in_location
            self.out_picking_type = self.inter_type2.out_picking_type or self.out_picking_type
            self.in_picking_type = self.inter_type2.in_picking_type or self.in_picking_type
            if self.inter_type2.duration and self.order_date:
                self.validity_date = fields.Datetime.from_string(self.order_date) + timedelta(
                    hours=self.inter_type2.duration)

    @api.multi
    def action_progress(self):
        self.write({'state': 'progress'})

    @api.onchange('inter_type', 'out_location', 'in_location')
    def _location_id_change(self):
        if not self.inter_type or not self.out_location or not self.in_location:
            return
        out_picking_type = in_picking_type = False
        if self.inter_type == '1step':
            domain = [('default_location_src_id', '=', self.out_location.id),
                      ('default_location_dest_id', '=', self.in_location.id)]
            out_picking_type = self.env['stock.picking.type'].search(domain, limit=1)
        else:
            transit_location = self.env.ref('stock_inter_transfer.location_inter_transit')
            domain = [('default_location_src_id', '=', self.out_location.id),
                      ('default_location_dest_id', '=', transit_location.id)]
            out_picking_type = self.env['stock.picking.type'].search(domain, limit=1)
            domain = [('default_location_src_id', '=', transit_location.id),
                      ('default_location_dest_id', '=', self.in_location.id)]
            in_picking_type = self.env['stock.picking.type'].search(domain, limit=1)
        if out_picking_type:
            self.out_picking_type = out_picking_type.id
        if in_picking_type:
            self.in_picking_type = in_picking_type.id

    @api.model
    def _prepare_inter_picking(self, picking_type, out_loc, in_loc, dt):
        return {
            'partner_id':self.partner_id.id,
            'picking_type_id': picking_type.id,
            'date': dt,
            'origin': self.name,
            'location_dest_id': in_loc.id,
            'location_id': out_loc.id,
            'company_id': self.company_id.id,
        }

    @api.multi
    def action_inter_picking(self):
        """两步调拨时候，在途库位优先从 Picking Type 取，取不到再取在途库位
        """
        self.ensure_one()
        StockPicking = self.env['stock.picking']
        inter_lines = self.inter_lines.filtered(
            lambda x: not x.out_picking_ids and x.product_id.type in ['product', 'consu'])

        if not inter_lines:
            raise UserError(_(u'没有需要关联出入库单的调拨明细行！'))

        out_loc = self.out_location
        in_loc = self.in_location
        int_loc = self.env.ref('stock_inter_transfer.location_inter_transit')
        if self.out_picking_type and self.in_picking_type and self.out_picking_type.default_location_dest_id and self.out_picking_type.default_location_dest_id == self.in_picking_type.default_location_src_id:
            int_loc = self.out_picking_type.default_location_dest_id

        if self.inter_type == '2step':
            in_loc = int_loc
        picking_data = self._prepare_inter_picking(self.out_picking_type, out_loc, in_loc, self.order_date)
        out_picking = StockPicking.create(picking_data)
        moves = inter_lines._create_stock_moves(out_picking)

        inter_lines.write({'out_picking_ids': [(4,out_picking.id)]})
        out_picking.message_post_with_view('mail.message_origin_link',
                                           values={'self': out_picking, 'origin': self},
                                           subtype_id=self.env.ref('mail.mt_note').id)

        if self.inter_type == '2step':
            # out_picking.button_validate()
            out_loc = int_loc
            in_loc = self.in_location
            picking_data = self._prepare_inter_picking(self.in_picking_type, out_loc, in_loc, self.validity_date)
            in_picking = StockPicking.create(picking_data)
            moves = inter_lines._create_stock_moves(in_picking)

            inter_lines.write({'in_picking_ids': [(4,in_picking.id)]})
            in_picking.message_post_with_view('mail.message_origin_link',
                                              values={'self': in_picking, 'origin': self},
                                              subtype_id=self.env.ref('mail.mt_note').id)

        return self.action_view_inter_picking()

    @api.multi
    def action_view_inter_picking(self):
        self.ensure_one()
        picking_ids = self.env['stock.picking']
        picking_ids |= self.inter_lines.mapped('out_picking_ids')
        picking_ids |= self.inter_lines.mapped('in_picking_ids')
        self.inter_picking_ids = picking_ids
        self.inter_picking_count = len(picking_ids)
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        if len(picking_ids) > 1:
            action['domain'] = [('id', 'in', picking_ids.ids)]
        elif len(picking_ids) == 1:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = picking_ids.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    @api.multi
    def action_view_out_lot(self):
        self.env['stock.quant']._merge_quants()
        action = self.env.ref('stock.quantsact').read()[0]
        action['domain'] = [('lot_id', '!=', False), ('location_id', 'child_of', [self.out_location.id])]
        action['context'] = {'group_by': ['lot_id']}
        return action

    @api.multi
    def action_done(self):
        self.write({'state': 'done'})

    @api.multi
    def action_cancel(self):
        for order in self:
            out_picking_ids = order.inter_lines.mapped('out_picking_ids')
            in_picking_ids = order.inter_lines.mapped('in_picking_ids')
            if out_picking_ids or in_picking_ids:
                raise UserError(_(u'取消调拨单之前，必须先取消并删除调拨单关联的所有出库单、入库单！'))
            order.write({'state': 'cancel'})

    @api.multi
    def action_reset(self):
        self.write({'state': 'draft'})

    @api.multi
    def unlink(self):
        for order in self:
            if order.state not in ['draft', ]:
                raise UserError(_(u'只可以删除草稿状态的调拨单！'))
        return super(StockInterPicking, self).unlink()


class StockInterLine(models.Model):
    _name = 'stock.inter.line'
    _description = u"调拨明细行"

    name = fields.Text("说明", copy=True)
    order_id = fields.Many2one('stock.inter.picking', string=u'调拨单', required=True, ondelete='cascade', copy=False)
    lot_id = fields.Many2one('stock.production.lot', string=u'批次号')
    package_id = fields.Many2one('stock.quant.package', string=u'箱号')
    product_id = fields.Many2one('product.product', string=u'产品')
    qty = fields.Float(string=u'数量', required=True)
    product_uom = fields.Many2one('uom.uom', related='lot_id.product_id.uom_id', string=u'单位', store=True)

    out_picking_ids = fields.Many2many('stock.picking', 'out_picking_rel', 'inter_line_id',
                                   'picking_id', string=u'关联调出单',copy=False)
    in_picking_ids = fields.Many2many('stock.picking', 'in_picking_rel', 'inter_line_id',
                                   'picking_id',string=u'关联调入单',copy=False)

    sequence = fields.Integer(string='Sequence', default=10)
    state = fields.Selection([
        ('draft', u'草稿'),
        ('progress', u'调拨中'),
        ('done', u'完成'),
        ('cancel', u'取消'),
    ], related='order_id.state', string=u'明细行状态', readonly=True, copy=False, store=True, default='draft')
    active = fields.Boolean(default=True, help="Set active to false to hide this order.")

    @api.onchange('lot_id')
    def _lot_id_change(self):
        self.product_id = self.lot_id.product_id.id
        self.name = '%s:%s' % (self.lot_id.name, self.lot_id.product_id.name)

    @api.onchange('product_id')
    def _product_id_change(self):
        # self.name = "[%s]%s" % (self.product_id.default_code, self.product_id.name)
        self.product_uom = self.product_id.uom_id.id

    @api.multi
    def _prepare_stock_moves(self, picking):
        self.ensure_one()
        res = []
        if self.product_id.type not in ['product', 'consu']:
            return res

        template = {
            'name': self.name or '',
            'product_id': self.product_id.id,
            'product_uom': self.product_uom.id,
            'product_uom_qty': self.qty,
            'date': picking.date,
            'date_expected': picking.date,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'picking_id': picking.id,
            'state': 'draft',
            'company_id': picking.company_id.id,
            'picking_type_id': picking.picking_type_id.id,
            'origin': self.order_id.name,
            'route_ids': picking.picking_type_id.warehouse_id and [
                (6, 0, [x.id for x in picking.picking_type_id.warehouse_id.route_ids])] or [],
            'warehouse_id': picking.picking_type_id.warehouse_id.id,
        }
        quant_uom = self.product_id.uom_id
        if self.product_uom.id != quant_uom.id and self.env['ir.config_parameter'].get_param('stock.propagate_uom') != '1':
            product_qty = self.product_uom._compute_quantity(self.qty, quant_uom, rounding_method='HALF-UP')
            template['product_uom'] = quant_uom.id
            template['product_uom_qty'] = product_qty
        return template

    @api.multi
    def _create_stock_moves(self, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        assigned_moves = self.env['stock.move']
        partially_available_moves = self.env['stock.move']
        for line in self:
            val = line._prepare_stock_moves(picking)
            move = moves.create(val)

            # move._action_confirm(merge=False)
            # done += move
            # need = move.product_qty
            # available_quantity = self.env['stock.quant']._get_available_quantity(move.product_id,
            #                                                                      move.location_id,
            #                                                                      lot_id=line.lot_id or None,
            #                                                                      package_id=line.package_id or None)
            # if available_quantity < need:
            #     raise UserError('%s中%s的%s的可用数量不足,当前为%s个.' % (
            #     move.location_id.name, line.lot_id.name, move.product_id.name, available_quantity))

            # # if available_quantity <= 0:
            # #     continue
            # taken_quantity = move._update_reserved_quantity(need, available_quantity, move.location_id,
            #                                                 lot_id=line.lot_id or None,
            #                                                 package_id=line.package_id or None, strict=False)

            # if float_is_zero(taken_quantity, precision_rounding=move.product_id.uom_id.rounding):
            #     continue
            # if need == taken_quantity:
            #     assigned_moves |= move
            # else:
            #     partially_available_moves |= move

            # values = {
            #         'move_id': move.id,
            #         'location_id': move.location_id.id,
            #         'location_dest_id': move.location_dest_id.id,
            #         'product_id': move.product_id.id,
            #         'date': move.date.strftime(DATE_FORMAT),
            #         'product_uom_id': move.product_id.uom_id.id,
            #         'product_uom_qty': move.product_uom_qty,
            #         'qty_done':move.product_uom_qty,
            #         'lot_id':line.lot_id.id,
            #         'picking_id':picking.id
            #     }
            # move.move_line_ids = [(6,0,[self.env['stock.move.line'].create(values).id])]



        # partially_available_moves.write({'state': 'partially_available'})
        # assigned_moves.write({'state': 'assigned'})
        # picking._check_entire_pack()

        picking.action_assign()
        for line in picking.mapped('move_lines').move_line_ids:
            inter_line = self.filtered(lambda l:l.product_id.id == line.product_id.id)
            line.write({'lot_id':inter_line.lot_id.id,'qty_done':line.product_uom_qty})

        return done

    @api.multi
    def unlink(self):
        for line in self:
            if line.in_picking_ids:
                raise UserError(_(u'删除明细行之前请删除明细行关联的调拨出库、入库单！'))
            if line.order_id.state in ['done', ]:
                raise UserError(_(u'调拨单已经完成，明细行不可删除！'))
        return super(StockInterLine, self).unlink()


class StockInterType(models.Model):
    _name = 'stock.inter.type'
    _description = u"调拨单区分"

    name = fields.Char("名称", required=True)
    code = fields.Char("代码")
    inter_type = fields.Selection([('1step', u'一步调拨'), ('2step', u'两步调拨'), ], string=u'默认调拨类型')
    out_location = fields.Many2one('stock.location', string=u'默认调出库')
    in_location = fields.Many2one('stock.location', string=u'默认调入库')
    out_picking_type = fields.Many2one('stock.picking.type', string=u'默认调出类型')
    in_picking_type = fields.Many2one('stock.picking.type', string=u'默认调入类型')
    duration = fields.Integer(string=u'默认在途时数', help="调出时间和调入时间间隔时数。")
    active = fields.Boolean(default=True, help="Set active to false to hide this order.")


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    out_inter_line_ids = fields.Many2many('stock.inter.line', 'out_picking_rel', 'picking_id',
                                   'inter_line_id', string=u'关联调出明细行',copy=False)
    in_inter_line_ids = fields.Many2many('stock.inter.line', 'in_picking_rel', 'picking_id',
                                   'inter_line_id',string=u'关联调入明细行',copy=False)

    def action_done(self):
        result = super().action_done()
        inter_lines = self.out_inter_line_ids or self.in_inter_line_ids
        inter_pickings = inter_lines.mapped('order_id')
        for each in inter_pickings:
            if not each.inter_picking_ids.filtered(lambda p:p.state != 'done'):
                each.write({'state':'done'})
        return result