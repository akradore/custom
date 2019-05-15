import time
import datetime
import requests
import hashlib
import urllib
import json

from odoo import http

from . import auth
from .. import constants
from .yzclient import YZClient


####################################
#
#   有赞开放平台SDK - 推送消息处理- Python 3.0.6
#
#      三方库依赖: requests
#
####################################

class YZPushService(object):
    def __init__(self, authorize):
        self.auth = authorize
        self.env = http.request.env

    def handle(self, request_data):
        """ request_data type is dict"""
        if request_data.get('test', False):
            return {"code": 0, "msg": "success"}

        if not self.check_sign(self.auth, request_data):
            raise Exception('Invalid Youzan push message: %s' % request_data)

        func_type = ''
        msg_dict = {}
        if request_data.get('type'):
            func_type = request_data.get('type')
            msg_dict = json.loads(urllib.parse.unquote(request_data['msg']))
            # dict([kv.split('=') for kv in request_data['msg'].split('&')])

        elif request_data.get('biz_type'):
            func_type = request_data.get('biz_type')
            msg_dict = json.loads(urllib.parse.unquote(request_data['msg']))

        func_type = 'youzan_%s' % func_type.lower()
        result = getattr(self, func_type)(**msg_dict)  ## exec func type
        return result

    def check_sign(self, sign, params):

        if not isinstance(sign, auth.Sign):
            raise Exception('Sign mode must specify typeof auth.Sign')

        check_message = sign.app_id + params['msg'] + sign.app_secret
        md5_sign = hashlib.md5(check_message.encode('utf-8')).hexdigest()
        return True  # or md5_sign == params['sign']

    def youzan_retail_open_delivery_order(self, response):
        """{
            "id":"20170807181905034500002",
            "kdt_id":164932,
            "msg":"%22delivery_order_no%22:%2220170807181905034500002%22,%22status%22:%22WAIT_DELIVER%22%7D",
            "msg_id":"201708071819050345000021502101079000",
            "biz_type":"retail_open_delivery_order",
            "version":1502101079000
        }
        response:
        {
          "response": {
            "postage": "0",
            "real_pay_amount": "3.89",
            "create_time": "2018-09-26 17:57:03",
            "dist_type": "TYPE_EXPRESS",
            "pay_amount": "3.89",
            "sale_way": "OFFLINE",
            "pay_way": 1,
            "warehouse_code": "POS_B",
            "delivery_order_no": "2018092617570300000100011",
            "buyer_info": {
              "buyer_phone": "18521388782",
              "buyer_id": 1111111,
              "buyer_name": "蒋微信",
            },
            "receiver_info": {
              "area": "西湖区",
              "province": "浙江省",
              "city": "杭州市",
              "detail_address": "学院路77号黄龙万科中心G座微信地址",
              "name": "蒋微信",
              "mobile": "15927190197"
            },
            "order_items": [
              {
                "unit": "件",
                "quantity": "1",
                "sku_no": "P180706960839920",
                "real_sales_price": "3.89",
                "output_tax_rate": "0",
                "sales_price": "3.89",
                "order_item_no": "1473863415224074244",
                "delivery_order_no": "201809261757030000010011",
                "sku_code": "SP000001",
                "product_name": "zyl商品发门店4-1"
              },
              {
                "unit": "件",
                "quantity": "1",
                "sku_no": "P180706960839920",
                "real_sales_price": "3.89",
                "output_tax_rate": "0",
                "sales_price": "3.89",
                "order_item_no": "1473863415224074245",
                "delivery_order_no": "201809261757030000010011",
                "sku_code": "SP000002",
                "product_name": "zyl商品发门店4-2"
              }
            ],
            "status": "DELIVERED"
          }
        }
        """
        yzclient = YZClient.get_default_client()

        params = {}
        params['delivery_order_no'] = response["delivery_order_no"]
        params['retail_source'] = constants.RETAIL_SOURCE

        # result = yzclient.invoke('youzan.retail.open.deliveryorder.get', '3.0.0', 'POST', params=params, files=[])
        # response = result['response']

        if response['sale_way'] != 'OFFLINE':
            return

        # STEP 1, create sale order from push message
        sale_order = self.env['sale.order'].sudo().search([
            ('origin', '=', response['delivery_order_no']),
            ('order_from', '=', constants.ORDER_FROM_YOUZAN_RETAIL)
        ], limit=1)

        if sale_order:
            return sale_order.id

        buyer, warehouse_code, pay_way = response['buyer_info'], response['warehouse_code'], response['pay_way']
        parter = self.env['res.partner'].sudo().search(
            ['|', ('ref', '=', buyer['buyer_id']), ('ref', '=', buyer['buyer_phone'])], limit=1)

        if not parter:
            parter = self.env['res.partner'].sudo().create({
                'name': buyer['buyer_name'],
                'date': response['create_time'],
                'ref': buyer['buyer_id'],
                'mobile': buyer['buyer_phone'],
                'customer': True,
            })

        ware_house = self.env['stock.warehouse'].sudo().search([('code', '=', warehouse_code)], limit=1)
        sale_order = self.env['sale.order'].sudo().create({
            # 'name': '',
            'origin': response['delivery_order_no'],
            'order_from': constants.ORDER_FROM_YOUZAN_RETAIL,
            'date_order': response['create_time'],
            'partner_id': parter and parter.id,
            'warehouse_id': ware_house and ware_house.id,
            'note': response.get('remark', None),
        })

        for item in response['order_items']:
            product = self.env['product.product'].sudo().search([('default_code', '=', item['sku_code'])], limit=1)
            self.env['sale.order.line'].sudo().create({
                'order_id': sale_order and sale_order.id,
                'product_id': product and product.id,
                'order_item_no': item['order_item_no'],
                'name': item['product_name'],
                'customer_lead': 2,  # post in 2 days
                'price_unit': item['real_sales_price'],
                'product_uom_qty': item['quantity'],
            })

        # STEP 2, confirm order, state quotation to wait send
        sale_order.action_confirm()

        # STEP 3, create order invoice in memory
        # order.line.product_id.invoice_policy = 'order' is valid
        inv_ids = sale_order.action_invoice_create()

        # STEP 4, open and save the invoice
        invoice = self.env['account.invoice'].sudo().browse(inv_ids)
        invoice.action_invoice_open()

        # TODO, here need to convert pay_way to inner account journal type
        bank_journal = self.env['account.journal'].sudo().search([('type', '=', 'cash'), ('code', '=', 'CSH1')], limit=1)
        # STEP 5, reconcile the invoice receipts
        invoice.pay_and_reconcile(bank_journal, invoice.amount_total)

        # STEP 6, deliver order -> stock pinking
        pickings = self.env['sale.order'].sudo().browse(sale_order.id).mapped('picking_ids') \
            .filtered(lambda p: p.state not in ('done', 'cancel'))

        result = pickings.button_validate()
        stock_transfer = self.env[result['res_model']].sudo().browse(result['res_id'])
        stock_transfer.process()

        # TODO ,handle exception and notice admin
        return sale_order.id

    def youzan_trade_order_state(self, **data):
        """{
            "client_id":"6cd25b3f99727975b5",
            "id":"E20170807181905034500002",
            "kdt_id":63077,
            "kdt_name":"Qi码运动馆",
            "mode":1,
            "msg":"%7B%22update_time%22:%222017-08-07%2018:19:05%22,%22payment%22:%2211.00%22,%22tid%22:%22E20170807181905034500002%22,%22status%22:%22TRADE_CLOSED%22%7D",
            "sendCount":0,
            "sign":"5c15274ca4c079197c89154f44b20307",
            "status":"TRADE_CLOSED",
            "test":false,
            "type":"TRADE_ORDER_STATE",
            "version":1502101273
        }"""

        print('trade_order_state, kw=%s' % data)
