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

    def __init__(self, authorize, env=None):
        self.auth = authorize
        self.env  = env or http.request.env

    @classmethod
    def DEFAULT_SETUP_PUSH_SERVICE(cls):
        authorize = auth.Sign(constants.YOUZAN_CLIENT_ID, constants.YOUZAN_CLIENT_SECRET)
        return cls(authorize)

    def handle(self, request_data):
        """ request_data type is dict"""
        if request_data['test'] or request_data['mode'] != 1:
            # if test and not develop mode , return success
            return {"code": 0, "msg": "success"}

        if not self.check_sign(self.auth, request_data):
            raise Exception('Invalid Youzan push message: %s' % request_data)

        # msg_dict = {}
        # if request_data.get('type'):
        func_type = request_data['type']
        msg_dict = json.loads(urllib.parse.unquote(request_data['msg']))
            # dict([kv.split('=') for kv in request_data['msg'].split('&')])

        # elif request_data.get('biz_type'):
        #     func_type = request_data.get('biz_type')
        #     msg_dict = json.loads(urllib.parse.unquote(request_data['msg']))

        func_type = 'youzan_%s' % func_type.lower()
        result = getattr(self, func_type)(msg_dict)  ## exec func type
        return result

    def check_sign(self, sign, params):

        if not isinstance(sign, auth.Sign):
            raise Exception('Sign mode must specify typeof auth.Sign')

        check_message = sign.app_id + params['msg'] + sign.app_secret
        md5_sign = hashlib.md5(check_message.encode('utf-8')).hexdigest()
        return md5_sign == params['sign']

    def youzan_retail_open_delivery_order_delivered(self, req_data):
        """
        data:
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
        """
        yzclient = YZClient.get_default_client()

        params = {}
        params['delivery_order_no'] = req_data["delivery_order_no"]
        params['retail_source'] = constants.RETAIL_SOURCE

        result = yzclient.invoke('youzan.retail.open.deliveryorder.get', '3.0.0', 'POST', params=params, files=[])
        data = result['data']

        if data['saleWay'] != 'OFFLINE':
            return False

        self.env['sale.order'].with_delay().create_youzan_retail_order_by_params(data)

        # TODO ,handle exception and notice admin
        return

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
