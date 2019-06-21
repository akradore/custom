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

        func_type = request_data['type']
        msg_dict = json.loads(urllib.parse.unquote(request_data['msg']))

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
            "delivery_order_no": ...
        }
        """

        params = {}
        params['delivery_order_no'] = req_data["delivery_order_no"]
        params['retail_source'] = constants.RETAIL_SOURCE

        debug = self.env['ir.config_parameter'].sudo().get_param(
            'mysale_youzan.mysale_youzan_push_message_is_debug_mode')

        yzclient = YZClient.get_default_client()
        result = yzclient.invoke('youzan.retail.open.deliveryorder.get', '3.0.0', 'POST',
                                 params=params,
                                 debug=debug)
        data = result['data']

        if data['saleWay'] != 'OFFLINE': # 线上消息通知只接收线下零售订单
            return False

        self.env['sale.order'].with_delay().create_youzan_retail_order_by_params(data)

        # TODO ,handle exception and notice admin
        return True

    def youzan_retail_open_goods_apply_order_to_check(self, req_data):
        """要货单消息通知，ERP内部审核
        {
            'apply_order_no': 'RO0021906120001'
        }"""

        params = {}
        params['apply_order_no'] = req_data["apply_order_no"]
        params['retail_source'] = constants.RETAIL_SOURCE

        debug = self.env['ir.config_parameter'].sudo().get_param(
            'mysale_youzan.mysale_youzan_push_message_is_debug_mode')

        yzclient = YZClient.get_default_client()
        result = yzclient.invoke('youzan.retail.open.applyorder.get', '3.0.0', 'POST',
                                 params=params,
                                 debug=debug)
        data = result['data']

        if data['status'] not in constants.APPLY_ORDER_STATUS_MAP.keys(): # 1-待审核 4-已驳回 5-已关闭 6-已完成 15-已审核
            return False

        self.env['mysale.stock.synchron'].with_delay().action_apply_order_create_or_update(data)

        return True

    def youzan_retail_open_stockout_order(self, req_data):
        """ 出库单创建消息类型 调拨出库:DBCK, 配送出库:PSCK, 盘亏出库:PKCK, 销售出库:XSCK, 报损出库:BSCK, 其它出库:QTCK；
        {
          "order_type": "DBCK",
          "biz_bill_no": "111",
          "warehouse_code": "123"
        }"""

        params = {}
        params['biz_bill_no'] = req_data["biz_bill_no"]
        params['retail_source'] = constants.RETAIL_SOURCE

        debug = self.env['ir.config_parameter'].sudo().get_param(
            'mysale_youzan.mysale_youzan_push_message_is_debug_mode')

        yzclient = YZClient.get_default_client()
        result = yzclient.invoke('youzan.retail.open.stockinorder.get', '3.0.0', 'POST',
                                 params=params,
                                 debug=debug)
        data = result['data']

        self.env['mysale.stock.synchron'].with_delay().action_apply_order_create_or_update(data)

        return True

    def youzan_retail_open_stockin_order(self, req_data):
        """ 入库单创建消息类型 调拨入库:DBRK, 配送入库:PSRK, 盘盈入库:PYRK, 退货入库:THRK, 采购入库:CGRK;
        {
          "order_type": "DBRK",
          "biz_bill_no": "111",
          "warehouse_code": "123"
        }"""

        params = {}
        params['biz_bill_no'] = req_data["biz_bill_no"]
        params['retail_source'] = constants.RETAIL_SOURCE

        debug = self.env['ir.config_parameter'].sudo().get_param(
            'mysale_youzan.mysale_youzan_push_message_is_debug_mode')

        yzclient = YZClient.get_default_client()
        result = yzclient.invoke('youzan.retail.open.stockinorder.get', '3.0.0', 'POST',
                                 params=params,
                                 debug=debug)
        data = result['data']

        self.env['mysale.stock.synchron'].with_delay().action_stockin_order_create(data)

        return True


    def youzan_retail_open_stockout_order(self, req_data):
        """ 出库单创建消息类型 调拨入库:DBRK, 配送入库:PSRK, 盘盈入库:PYRK, 退货入库:THRK, 采购入库:CGRK;
        {
          "order_type": "DBRK",
          "biz_bill_no": "111",
          "warehouse_code": "123"
        }"""

        params = {}
        params['biz_bill_no'] = req_data["biz_bill_no"]
        params['retail_source'] = constants.RETAIL_SOURCE

        debug = self.env['ir.config_parameter'].sudo().get_param(
            'mysale_youzan.mysale_youzan_push_message_is_debug_mode')

        yzclient = YZClient.get_default_client()
        result = yzclient.invoke('youzan.retail.open.stockoutorder.get', '3.0.0', 'POST',
                                 params=params,
                                 debug=debug)
        data = result['data']

        self.env['mysale.stock.synchron'].with_delay().action_stockout_order_create(data)

        return True
