# -*- coding: utf-8 -*-
# 1 : imports of python
import json
import logging

# 2 : imports of odoo
from odoo import _, api, exceptions, fields, http, models, tools
from odoo.http import request
from odoo.http import Response

# 3 : imports of custom module
from .. import odoo_http
from ..yzsdk import Sign, YZPushService

# 4 : variable declarations
_logger = logging.getLogger(__name__)

class YouzanRetail(http.Controller):

    @classmethod
    def youzan_push_service(cls):
        return YZPushService.DEFAULT_SETUP_PUSH_SERVICE()

    #
    # @http.route('/mysale_youzan/mysale_youzan/objects/', auth='public')
    # def list(self, **kw):
    #     return http.request.render('mysale_youzan.listing', {
    #         'root': '/mysale_youzan/mysale_youzan',
    #         'objects': http.request.env['mysale_youzan.mysale_youzan'].search([]),
    #     })
    #
    # @http.route('/mysale_youzan/mysale_youzan/objects/<model("mysale_youzan.mysale_youzan"):obj>/', auth='public')
    # def object(self, obj, **kw):
    #     return http.request.render('mysale_youzan.object', {
    #         'object': obj
    #     })

    @odoo_http.route2('/mysale_youzan/push/receive/', type='json2', auth='public' , csrf=False)
    def push_receive(self, **request_data):
        """ 有赞消息通知统一处理接口 """
        self._write_to_debug_log('Youzan Push Messsage', data=json.dumps(request_data, indent=2))

        yz_psrv = YouzanRetail.youzan_push_service()
        yz_psrv.handle(request_data)

        return {"code":0,"msg":"success"}


    def _write_to_debug_log(self, title, data=False):

        if request.env['ir.config_parameter'].sudo().get_param('mysale_youzan.mysale_youzan_push_message_is_debug_mode'):
            debug_title = "========" + title + " ========"
            _logger.debug(debug_title)
            if data:
                _logger.debug(data)
        else:
            pass



