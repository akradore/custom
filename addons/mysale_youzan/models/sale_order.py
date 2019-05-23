# -*- coding: utf-8 -*-
import datetime
import logging

from odoo import models, fields, api
from odoo.addons.queue_job.job import job

from ..yzsdk import YZClient
from .. import constants

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _gen_partner_ref_unikey(self, buyer_phone, buyer_id):
        # default use buyer_phone
        if not buyer_phone:
            return '_%s' % (buyer_id or 0)
        return 's%_s%' % (buyer_phone, str(buyer_id or 0))

    # ex_order_from = fields.Selection([
    #     ('default', 'DEFAULT'),
    #     ('yz_retail', 'YOUZAN Retail'),
    #     ('taobao', 'TAOBAO'),
    #     ('jd', 'JINGDONG'),
    #     ('yz_mall', 'YOUZAN MALL'),
    #     ], string='来自平台', readonly=True, copy=False, index=True, track_visibility='onchange', track_sequence=3, default='default')

    # [res.partner]
    # ref => fields.Char(string='Internal Reference', index=True)
    # ref = '[buyer_id]_[buyer_phone]'

    @api.model
    @job
    def create_youzan_retail_order_by_params(self, data):
        """ 6 STEPS, create a saleorder by youzan retail order
        {
            "orderNo": "E20190514141210006500015",
            "refundInfos": null,
            "orderCreateTime": "2019-05-14 14:12:10",
            "receiverInfo": {
                "area": "",
                "province": "",
                "city": "",
                "mobile": "",
                "name": "",
                "detailAddress": "",
                "tel": null
            },
            "payWay": 43,
            "updateTime": "2019-05-14 14:12:31",
            "remark": null,
            "distType": "TYPE_ALL",
            "warehouseName": "米娅公主测试门店",
            "orderItems": [
                {
                    "refundFee": null,
                    "itemType": 0,
                    "quantity": "4",
                    "salesPrice": "32",
                    "weight": null,
                    "productName": "枸杞瓶装",
                    "realSalesAmount": "118",
                    "outputTaxRate": "0",
                    "deliveryOrderNo": "201905141412110000010000",
                    "unit": "瓶",
                    "realSalesPrice": "118",
                    "orderItemNo": "1516509233779581742",
                    "pricingStrategy": 0,
                    "skuNo": "P190514419369477",
                    "skuCode": "30104"
                }
            ],
            "warehouseCode": "POS_A",
            "realSalesAmount": "118",
            "deliveryOrderNo": "201905141412110000010000",
            "postage": "0",
            "buyerInfo": {
                "buyerRemark": "",
                "buyerPhone": null,
                "fansNickname": "",
                "isMember": false,
                "buyerId": 567970881,
                "buyerName": null
            },
            "payType": 5,
            "payWayDesc": "现金支付",
            "createTime": "2019-05-14 14:12:10",
            "salesAmount": "128",
            "saleWay": "OFFLINE",
            "status": "DELIVERED",
            "cashierInfo": {
                "cashierId": "8222281386",
                "cashierName": "王俊"
            }
        }
        """
        try:
            # STEP 1, create sale order from push message
            sale_order = self.env['sale.order'].sudo().search([
                ('origin', '=', data['orderNo']),
                ('order_from', '=', constants.ORDER_FROM_YOUZAN_RETAIL)
            ], limit=1)

            if sale_order:
                return sale_order

            buyer, warehouse_code, pay_way = data['buyerInfo'], data['warehouseCode'], data['payWay']
            parter = self.env['res.partner'].sudo().search(
                ['|', ('ref', '=like', '%' + str(buyer['buyerId'] or '0')),
                 ('ref', '=like', str(buyer['buyerPhone'] or 'null') + '%')], limit=1)

            if not parter:
                parter = self.env['res.partner'].sudo().create({
                    'name': buyer['buyerName'] or buyer['buyerPhone'] or str(buyer['buyerId']),
                    'type': 'contact',
                    'date': data['createTime'],
                    'ref': self._gen_partner_ref_unikey(buyer['buyerPhone'], buyer['buyerId']),
                    'mobile': buyer['buyerPhone'],
                    'customer': True,
                })

            ware_house = self.env['stock.warehouse'].sudo().search([('code', '=', warehouse_code)], limit=1)
            sale_order = self.env['sale.order'].sudo().create({
                # 'name': '',
                'origin': data['orderNo'],
                'order_from': constants.ORDER_FROM_YOUZAN_RETAIL,
                'date_order': data['createTime'],
                'partner_id': parter and parter.id,
                'warehouse_id': ware_house and ware_house.id,
                'note': data.get('remark', None),
            })

            for item in data['orderItems']:
                product = self.env['product.product'].sudo().search([('default_code', '=', item['skuCode'])], limit=1)
                self.env['sale.order.line'].sudo().create({
                    'order_id': sale_order and sale_order.id,
                    'product_id': product and product.id,
                    'order_item_no': item['orderItemNo'],
                    'name': item['productName'],
                    # 'customer_lead': 2,  # post in 2 days
                    'price_unit': float(item['realSalesPrice']) / float(item['quantity']),
                    'product_uom_qty': item['quantity'],
                })


            # STEP 2, confirm order ,change state quotation to wait send
            sale_order.action_confirm()

            # STEP 3, create order invoice in memory
            # order.line.product_id.invoice_policy = 'order' is valid
            inv_ids = sale_order.action_invoice_create()

            # STEP 4, open and save the invoice
            invoice = self.env['account.invoice'].sudo().browse(inv_ids)
            invoice.action_invoice_open()

            # TODO, here need to convert pay_way to inner account journal type
            bank_journal = self.env['account.journal'].sudo().search([('type', '=', 'cash'), ('code', '=', 'CSH1')],
                                                                     limit=1)
            # STEP 5, reconcile the invoice receipts
            invoice.pay_and_reconcile(bank_journal, invoice.amount_total)

            # STEP 6, deliver order -> stock pinking
            pickings = self.env['sale.order'].sudo().browse(sale_order.id).mapped('picking_ids') \
                .filtered(lambda p: p.state not in ('done', 'cancel'))

            result = pickings.button_validate()
            stock_transfer = self.env[result['res_model']].sudo().browse(result['res_id'])
            stock_transfer.process()

        except Exception as exc:
            post_msg = 'SaleOrder(origin=%s) from %s has encounter an error: %s' % (
                     data['orderNo'], 'YouZan Retail', str(exc))

            _logger.error(post_msg)
            self.env['mail.thread'].sudo().message_post(
                model='sale.order',
                body=post_msg,
                message_type='notification',
                author_id=1,
                partner_ids=[1]
            )
            raise exc

        return sale_order

    @api.model
    def cron_youzan_retail_order_from_last_updated(self):
        """
        api response:
        {
            "deliveryOrders": [
                ...
            ],
            "paginator": {
                "pageSize": 20,
                "page": 1,
                "totalCount": 2
            }
        }
        :return:
        """
        update_start_str = self.env['ir.config_parameter'].sudo().get_param(
            'mysale_youzan.mysale_youzan_retail_order_last_update')

        if not update_start_str:
            update_start_str = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')

        update_end = datetime.datetime.now()

        yzclient = YZClient.get_default_client()

        params = {
            'status': 'DELIVERED',
            'update_time_start': update_start_str,
            'update_time_end': update_end.strftime('%Y-%m-%d %H:%M:%S'),
            'retail_source': constants.RETAIL_SOURCE,
            # 'admin_id': constants.YOUZAN_API_ADMIN_ID
        }

        page_no = 1
        has_next_page = True

        while has_next_page:

            params.update({
                'page_no': page_no,
                'page_size': 20
            })
            access_token = self.env['res.config.settings'].get_youzan_access_token()
            result = yzclient.invoke('youzan.retail.open.deliveryorder.query', '3.0.0', 'POST', params=params,
                                     files=[], access_token=access_token)
            delivery_orders, paginator = result['data']['deliveryOrders'], result['data']['paginator']

            for order_data in delivery_orders:
                self.with_delay().create_youzan_retail_order_by_params(order_data)

            has_next_page = paginator['page'] <= paginator['totalCount'] * 1.0 / paginator['pageSize']
            if has_next_page:
                page_no = paginator['page'] + 1

        self.env['ir.config_parameter'].sudo().set_param('mysale_youzan.mysale_youzan_retail_order_last_update',
                                                         update_end)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # order_item_no = fields.Char(String='Youzan Retail OrderItemNo', readonly=True, index=True)
