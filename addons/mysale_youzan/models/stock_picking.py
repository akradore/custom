# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from .. import constants

class Picking(models.Model):
    _inherit = "stock.picking"

    @api.returns('stock.picking', lambda value: value.id)
    def get_rule_push_stock_picking(self):
        """ Returns warehouse id of warehouse that contains location """
        domain = [('origin', '=', self.name),
                  ('state', 'in', ('assigned', 'done'))]
        return self.env['stock.picking'].search(domain, limit=1)

    @api.multi
    def action_done(self):
        super(Picking, self).action_done()

        if self.source_order_type == 'apply_order':
            # TODO 完成要货单入库，要货单确认，要货配送单出库
            pass

        elif self.picking_type_id.id not in constants.ZC2RS_WH_IN_PICKING_TYPE_IDS: # 如果是直赔
            self.action_done_create_stock_synchron()

        return True

    @api.one
    def action_done_create_stock_synchron(self):

        rp_auto_picking = self.get_rule_push_stock_picking() # 获取配货自动门店到货单
        f_wh = self.location_id.get_warehouse()
        t_wh = rp_auto_picking.location_dest_id.get_warehouse()

        synchron = self.env['mysale.stock.synchron'].create({
            'name': self.name,
            'source': self.origin,
            'order_type_code': 'distribution',
            'sync_type_code': 'odoo2youzan',
            'from_warehouse_code': f_wh.code,
            'to_warehouse_code': t_wh.code,
            'from_warehouse_name': f_wh.name,
            'to_warehouse_name': t_wh.name,
            'note': self.note
        })

        for line in self.move_lines:
            item = self.env['mysale.stock.synchron.item'].create({
                'name': line.product_id.name,
                'stock_synchron_id': synchron.id,
                'sku_code': line.product_id.default_code,
                'product_id': line.product_id.id,
                'unit': line.product_id.uom_id.name,
                'product_uom_id': line.product_id.uom_id.id,
                'quantity': line.product_qty,
                'pre_out_num': line.product_qty,
                'delivery_cost': line.price_unit,
            })
            item.move_ids += line

        synchron.with_delay().action_retail_open_distributionorder_create() # 异步更新配货单到有赞

        return True

    @api.model
    def action_stock_synchron_in_confirm_picking_receive(self, stock_synchron):

        s_picking = self.env['stock.picking'].search([('name','=',stock_synchron.source)])
        r_picking = s_picking.get_rule_push_stock_picking()  # 获取配货自动门店到货单
        t_wh = r_picking.location_dest_id.get_warehouse()

        if stock_synchron.to_warehouse_code != t_wh.code:
            return

        for move in r_picking.move_lines:
            line = move.move_lines
            if len(line) != 1:
                raise ValueError('stock.move and stock.move.line are not one to one relationship.')

            syn_item = stock_synchron.synchron_items.search([('product_id', '=', line.product_id.id)])
            line.write({
                'product_uom_qty': syn_item.quantity,
            })
            syn_item.move_ids += line

        return True