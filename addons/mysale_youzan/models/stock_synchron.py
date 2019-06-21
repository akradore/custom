# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.queue_job.job import job

from .. import constants
from ..yzsdk import YZClient


class StockSynchron(models.Model):
    _inherit = 'mysale.stock.synchron'

    order_type = fields.Selection([
        ('PSCK', '配送出库'),
        ('BSCK', '报损出库'),
        ('PKCK', '盘亏出库'),
        ('DBCK', '调拨出库'),
        ('YHTHCK', '要货退货出库'),
        ('BYRK', '报溢入库'),
        ('PYRK', '盘盈入库'),
        ('CGRK', '采购入库'),
        ('THRK', '退货入库'),
        ('DBRK', '调拨入库')],
        string='出入库单据类型',
        states={'done': [('readonly', True)]})

    @api.one
    def is_apply_order(self):
        return self.order_type_code == 'apply_stock' and self.sync_type_code == 'youzan2odoo'

    @api.one
    def is_distribution_order(self):
        return self.order_type_code == 'distribution' and self.sync_type_code == 'odoo2youzan'

    @api.one
    def is_apply_check_request(self):
        return self.order_type_code == 'apply_check' and self.sync_type_code == 'odoo2youzan'

    @api.one
    def is_stockin_order(self):
        return self.order_type_code == 'stockin_order' and self.sync_type_code == 'youzan2odoo'


    ##############################期初库存调整单#################################
    @api.multi
    @job
    def action_retail_open_stock_adjust(self):
        """ 期初库存调整单 """
        self.ensure_one()

        data = {
            'operate_type': 0, # 1增加，2减少，0绝对值
            'creator': '',
            'retail_source': constants.RETAIL_SOURCE,
            'create_time': self.data_order,
            'warehouse_code': self.to_warehouse_code,
            'remark': self.note or '',
            'source_order_no': self.source or self.name,
            'order_items': []
        }

        for item in self.synchrone_items:
            data['order_items'].append({
                'sku_code': item.sku_code,
                'quantity': '%.3f' % item.pre_out_num,
                'with_tax_cost': '%.4f' % item.with_tax_cost,
                'with_tax_amount': '%.4f' % item.with_tax_amount,
                'with_tax_income': '%.4f' % item.with_tax_income,
            })

        yzclient = YZClient.get_default_client()
        access_token = self.env['res.config.settings'].get_youzan_access_token()
        debug = self.env['ir.config_parameter'].sudo().get_param(
            'mysale_youzan.mysale_youzan_push_message_is_debug_mode')
        try:
            result = yzclient.invoke('youzan.retail.open.stock.adjust', '3.0.0', 'POST',
                                     params=data,
                                     files=[],
                                     access_token=access_token,
                                     debug=debug)
        except Exception as exc:
            self.write({
                'refused_reason': str(exc),
                'state': 'fail'
            })
            raise exc

        else:
            self.write({
                'done_data': fields.datetime.now(),
                # 'source': result['data'],
                # 'state': 'done'
            })

        return True

    ##############################要货单/配送单/统配单#################################
    # 业务说明：
    # 1, 接收有赞门店要货单创建消息；
    # 2, odoo根据有赞要货单创建配货单；
    # 3, odoo审核配货单创建有赞配货单；
    # 4, odoo配货单出仓包裹单创建有赞出仓单；
    # 5, 有赞入仓单创建odoo到货入仓包裹单；
    # 6, 有赞要货单完成或取消更新对应odoo要货单状态；

    @job
    def action_apply_order_create_or_update(self, data):
        """ step 1, 要货申请单信息入库 """

        sso_set = self.search(['name', '=', data['apply_biz_no']])
        sso_set_len = len(sso_set)
        if sso_set_len > 1:
            raise Exception('要货单重复: %s' % data['apply_biz_no'])

        state = constants.APPLY_ORDER_STATUS_MAP.get(data['status'], 'create')
        if sso_set_len == 0:
            sso = self.env['mysale.stock.synchron'].create({
                'name': data['apply_biz_no'],
                'order_type_code': 'apply_stock',
                'sync_type_code': 'youzan2odoo',
                'from_warehouse_code': data['from_warehouse_code'],
                'to_warehouse_code': data['to_warehouse_code'],
                'from_warehouse_name': data['from_warehouse_name'],
                'to_warehouse_name': data['to_warehouse_name'],
                'note': data['remark'],
                'refused_reason': data['refused_reason'],
            })

        else:
            sso = sso_set[0]
            if state == 'cancel':
                move_ids = sso.synchron_items.mapped('move_ids')
                move_ids.mapped('picking_id').action_cancel()

            sso.write({
                'state': state
            })

        for item in data['order_items']:
            ori_item = self.env['mysale.stock.synchron.item'].search([('sku_code','=',item['sku_code'])])
            product = self.env['product.product'].search([('default_code', '=', item['sku_code'])])
            product_uom = self.env['uom.uom'].search([('name', '=', item['unit'])])

            if not ori_item:
                self.env['mysale.stock.synchron.item'].create({
                    'stock_synchron_id': sso.id,
                    'name': item['product_name'],
                    # 'supplier_code': 'apply_stock',
                    'sku_code': item['sku_code'],
                    'product_id': product.id,
                    'unit': item['unit'],
                    'product_uom_id': product_uom.id,

                    'quantity': item['apply_num'],
                    'pre_out_num': item['pre_out_num'],
                    'actual_out_num': item['actual_out_num'],
                    'actual_in_num': item['actual_in_num'],

                    'with_tax_cost': item['with_tax_cost'],
                    'with_tax_amount': item['with_tax_amount'],
                    'with_tax_income': item['with_tax_income'],
                    'without_tax_amount': item['without_tax_amount'],
                    'without_tax_cost': item['without_tax_cost'],
                    'checked_delivery_cost': item['checked_delivery_cost'],
                    'delivery_cost': item['delivery_cost'],

                    'state': state,
                })
            else:
                ori_item.write({
                    'pre_out_num': item['pre_out_num'],
                    'actual_out_num': item['actual_out_num'],
                    'actual_in_num': item['actual_in_num'],

                    'with_tax_cost': item['with_tax_cost'],
                    'with_tax_amount': item['with_tax_amount'],
                    'with_tax_income': item['with_tax_income'],
                    'without_tax_amount': item['without_tax_amount'],
                    'without_tax_cost': item['without_tax_cost'],
                    'checked_delivery_cost': item['checked_delivery_cost'],
                    'delivery_cost': item['delivery_cost'],

                    'state': state,
                })
        # 创建配货单
        if sso_set_len == 0 and state in ('create', 'check'):
            sso.action_apply_order_create_stock_picking()

        return True

    @api.one
    @job
    def action_apply_order_create_stock_picking(self):
        """ step 2, 根据有赞叫货单创建odoo配送单 """

        if not self.is_apply_order():
            return False

        location_id = self.from_warehouse.int_type_id.default_location_src_id
        location_dest_id = self.to_warehouse.int_type_id.default_location_src_id

        if not (location_id and location_dest_id):
            return False

        picking = self.env['stock.picking'].create({
            'origin': self.name,
            'picking_type_id': self.from_warehouse.int_type_id.id,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'owner_id': self.owner_id,
            'state': 'draft',
        })

        for item in self.move_lines:
            st_move = self.env['stock.move'].create({
                'name': '%s-%s' % (self.name ,self.sku_code) ,
                'product_id': self.product_id.id,
                'product_uom_qty': self.quantity,
                'product_uom': self.product_uom_id,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'picking_id': picking.id,
                'state': 'draft',
            })

            item.move_ids += st_move

        return True

    @api.one
    @job
    def action_apply_order_check(self):
        """ step 3 审核有赞叫货单（odoo配货单检查可用性后调用,有赞自动生成配货单） """

        if not self.is_apply_check_request():
            return False

        data = {
            'retail_source': constants.RETAIL_SOURCE,
            'from_warehouse_code': self.from_warehouse_code,
            'admin_id': self.owner_id.ref,
            'apply_order_no': self.apply_order_no,
            'items': []
        }

        for item in self.synchron_items:
            data['items'].append({
                'sku_code': self.product_id.default_code,
                'checked_delivery_cost': self.checked_delivery_cost,
                'num': self.quanlity,
            })

        yzclient = YZClient.get_default_client()
        access_token = self.env['res.config.settings'].get_youzan_access_token()
        debug = self.env['ir.config_parameter'].sudo().get_param(
            'mysale_youzan.mysale_youzan_push_message_is_debug_mode')

        try:
            result = yzclient.invoke('youzan.retail.open.applyorder.check', '3.0.0', 'POST',
                                     params=data,
                                     files=[],
                                     access_token=access_token,
                                     debug=debug)

        except Exception as exc:
            self.write({
                'refused_reason': str(exc),
                'state': 'fail'
            })
            raise exc

        else:
            self.write({
                'done_data': fields.datetime.now(),
                'result_no': result['data'],
                # 'state': 'done'
            })

        return True


    @api.one
    @job
    def action_retail_open_distributionorder_create(self):
        """ 总部统配门店配货单至有赞（非要货场景） """

        if not self.is_distribution_order():
            return False

        data = {
            'biz_bill_no': self.source or self.name,
            'from_warehouse_code': self.from_warehouse_code,
            'to_warehouse_code': self.to_warehouse_code,
            'remark': self.note or '',
            'retail_source': constants.RETAIL_SOURCE,
            'kdt_id': constants.YOUZAN_AUTHORITY_ID,
            'order_items': []
        }

        for item in self.synchrone_items:
            data['order_items'].append({
                'sku_code': item.sku_code,
                'apply_num': '%s' % item.pre_out_num,
                'delivery_price_str': '0'  # TODO 配送价加盟店要货必填
            })

        yzclient = YZClient.get_default_client()
        access_token = self.env['res.config.settings'].get_youzan_access_token()
        debug = self.env['ir.config_parameter'].sudo().get_param(
            'mysale_youzan.mysale_youzan_push_message_is_debug_mode')
        try:
            result = yzclient.invoke('youzan.retail.open.distributionorder.create', '3.0.0', 'POST',
                                     params={'request': data},
                                     files=[],
                                     access_token=access_token,
                                     debug=debug)

        except Exception as exc:
            self.write({
                'refused_reason': str(exc),
                'state': 'fail'
            })
            raise exc

        else:
            self.write({
                'done_data': fields.datetime.now(),
                'source': result['data'],
                # 'state': 'done'
            })

        return True

    ##############################出库单/入库单#################################

    @api.model
    @job
    def action_stockout_order_create(self, data):
        """ step 5.1 根据有赞配送入仓单创建odoo配送到货单(入库单消息统一处理方法） """

        # PSCK=配送出库; BSCK=报损出库;PKCK=盘亏出库;DBCK=调拨出库; YHTHCK=要货退货出库

        sso = self.env['mysale.stock.synchron'].create({
            'name': data['biz_bill_no'],
            'source': data['source_order_no'],
            'order_type_code': 'stockin_order',
            'sync_type_code': 'youzan2odoo',
            'order_type': data['order_type'],
            'to_warehouse_code': data['warehouse_code'],
            'note': data['remark'],
            'refused_reason': data['refused_reason'],
            'data_order': data['create_time'],
            'state': 'create'
        })

        for item in data['order_items']:
            product = self.env['product.product'].search([('default_code', '=', item['sku_code'])])
            product_uom = self.env['uom.uom'].search([('name', '=', item['unit'])])
            self.env['mysale.stock.synchron.item'].create({
                'stock_synchron_id': sso.id,
                'name': item['product_name'],
                # 'supplier_code': 'apply_stock',
                'sku_code': item['sku_code'],
                'product_id': product.id,
                'unit': item['unit'],
                'product_uom_id': product_uom.id,
                'quantity': item['quantity'],

                'with_tax_cost': item['with_tax_cost'],
                'with_tax_amount': item['with_tax_amount'],
                'with_tax_income': item['with_tax_income'],
                'without_tax_amount': item['without_tax_amount'],
                'without_tax_cost': item['without_tax_cost'],
                'checked_delivery_cost': item['checked_delivery_cost'],
                'delivery_cost': item['delivery_cost'],
                'state': 'create',
            })

        return sso

    @api.one
    @job
    def action_stockout_order_done(self):
        """ step 4 odoo调拨出库包裹单创建有赞配送出库单（在配送单分配包裹验证后调用）"""

        # PSCK=配送出库; BSCK=报损出库;PKCK=盘亏出库;DBCK=调拨出库; YHTHCK=要货退货出库

        if not (self.order_type_code == 'stockout_order'
                and self.sync_type_code == 'odoo2youzan'
                and self.order_type == 'PSCK'):
            return

        data = {
            'biz_bill_no': self.name,  # 包裹编号
            'source_order_no': self.source,  # 关联配送单号
            'order_type': 'PSCK',
            'creator': self.owner_id.name,  # 配送单号
            'admin_id': self.owner_id.ref,  # 配送单号
            'create_time': self.data_order.strftime('%Y-%m-%d %H:%M:%S'),  # 配送单号
            'warehouse_code': self.to_warehouse_code,  # 配送单号
            'retail_source': constants.RETAIL_SOURCE,  # 配送单号
            'remark': self.note,  # 配送单号

            'logistics_company_id': self.package_id.logistics_company_id.name,  # 物流公司
            'logistics_order_no': self.package_id.logistics_no,  # 运单号
            'order_items': []  # 配送单号
        }

        for item in self.synchron_items:
            data['order_items'].append({
                'sku_code': item.sku_code,
                'quantity': item.quantity,
                'with_tax_cost': item.with_tax_cost,
                'with_tax_amount': item.with_tax_amount,
            })

        yzclient = YZClient.get_default_client()
        access_token = self.env['res.config.settings'].get_youzan_access_token()
        debug = self.env['ir.config_parameter'].sudo().get_param(
            'mysale_youzan.mysale_youzan_push_message_is_debug_mode')
        try:
            result = yzclient.invoke('youzan.retail.open.stockoutorder.create', '3.0.0', 'POST',
                                     params=data,
                                     files=[],
                                     access_token=access_token,
                                     debug=debug)

        except Exception as exc:
            self.write({
                'refused_reason': str(exc),
                'state': 'fail'
            })
            raise exc

        else:
            self.write({
                'done_data': fields.datetime.now(),
                'result_no': result['data'],
                # 'state': 'done'
            })

        return True

    @api.model
    @job
    def action_stockin_order_create(self, data):
        """ step 5.1 根据有赞配送入仓单创建odoo配送到货单(入库单消息统一处理方法） """

        # PSRK=配送入库 BYRK=报溢入库;PYRK=盘盈入库;CGRK=采购入库;THRK=退货入库;DBRK=调拨入库

        sso = self.env['mysale.stock.synchron'].create({
            'name': data['biz_bill_no'],
            'source': data['source_order_no'],
            'order_type_code': 'stockin_order',
            'sync_type_code': 'youzan2odoo',
            'order_type': data['order_type'],
            'to_warehouse_code': data['warehouse_code'],
            'note': data['remark'],
            'refused_reason': data['refused_reason'],
            'data_order': data['create_time'],
            'state': 'create'
        })

        for item in data['order_items']:
            product = self.env['product.product'].search([('default_code', '=', item['sku_code'])])
            product_uom = self.env['uom.uom'].search([('name', '=', item['unit'])])
            self.env['mysale.stock.synchron.item'].create({
                'stock_synchron_id': sso.id,
                'name': item['product_name'],
                # 'supplier_code': 'apply_stock',
                'sku_code': item['sku_code'],
                'product_id': product.id,
                'unit': item['unit'],
                'product_uom_id': product_uom.id,
                'quantity': item['quantity'],

                'with_tax_cost': item['with_tax_cost'],
                'with_tax_amount': item['with_tax_amount'],
                'with_tax_income': item['with_tax_income'],
                'without_tax_amount': item['without_tax_amount'],
                'without_tax_cost': item['without_tax_cost'],
                'checked_delivery_cost': item['checked_delivery_cost'],
                'delivery_cost': item['delivery_cost'],
                'state': 'create',
            })

        return sso

    @api.one
    @job
    def action_stockin_order_done(self, data):
        """ step 5.2 根据有赞配送入仓单创建odoo配送到货单(入库单消息统一处理方法） """

        # PSRK=配送入库 BYRK=报溢入库;PYRK=盘盈入库;CGRK=采购入库;THRK=退货入库;DBRK=调拨入库
        pass



class StockSynchronItem(models.Model):
    _inherit = 'mysale.stock.synchron.item'
