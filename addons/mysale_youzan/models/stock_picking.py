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

        self.action_done_create_stock_synchron()

        return True

    @api.multi
    def action_done_create_stock_synchron(self):
        self.ensure_one()

        if self.picking_type_id.id not in constants.ZC2RS_WH_IN_PICKING_TYPE_IDS:
            return False

        rp_auto_picking = self.get_rule_push_stock_picking() # 获取配货自动门店到货单
        f_wh = self.location_id.get_warehouse()
        t_wh = rp_auto_picking.location_dest_id.get_warehouse()

        synchron = self.env['mysale.stock.synchron'].create({
            'name': self.name,
            'order_type_code': 'distribution',
            'sync_type_code': 'odoo2youzan',
            'from_warehouse_code': f_wh.code,
            'to_warehouse_code': t_wh.code,
            'from_warehouse_name': f_wh.name,
            'to_warehouse_name': t_wh.name,
            'note': self.note
        })

        for line in self.move_lines:
            self.env['mysale.stock.synchron.item'].create({
                'name': line.product_id.name,
                'stock_synchron_id': synchron.id,
                'sku_code': line.product_id.default_code,
                'unit': line.product_id.uom_id.name,
                'quantity': line.product_qty,
                'delivery_cost': line.price_unit
            })

        synchron.action_distributionorder_create() # 同步配货单到有赞

        return True