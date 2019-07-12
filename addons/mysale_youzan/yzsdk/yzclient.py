from . import auth
import time
import requests
import hashlib
import json
import logging
import uuid

from odoo.http import request

from .. import constants
from .. import tools

_logger = logging.getLogger(__name__)

####################################
#
#   有赞开放平台SDK - 连锁接口处理- Python 3.0.6
#   三方库依赖: requests
#   有赞云平台参考文档： https://doc.youzanyun.com/doc#/content/API/1-299
#
####################################

class YZClient:
    def __init__(self, authorize):
        if not isinstance(authorize, auth.Token):
            raise ValueError('Invalid Youzan Token Instance!')
        self.auth = authorize

    @classmethod
    def get_default_client(cls):
        token = auth.Token.DEFAULT_SETUP_TOKEN()
        return cls(token)


    def invoke(self, apiName, version, method, params={}, files={}, access_token=None, http_url=None, debug=False):
        http_url = http_url or constants.YOUZAN_API_GETWAY
        serial = None

        if not access_token:
            access_token = request.env['res.config.settings'].get_youzan_access_token()

        http_url = http_url + '/' + apiName + '/' + version + '?access_token=%s' % access_token

        if debug: # 请求前调试日志
            serial = uuid.uuid4().hex
            _logger.debug(json.dumps({
                'serial': serial,
                'http_url': http_url,
                'method': method,
                'params': params,
                'files': files,
            }))

        resp = self.send_request(http_url, method, params, files)

        if debug: # 请求响应调试日志
            _logger.debug(json.dumps({
                'serial': serial,
                'response': str(resp.content, 'utf-8'),
            }))

        if resp.status_code != 200:
            ##TODO need to notify admin
            raise Exception('Invalid Youzan Response (status, text): %s,%s' %( resp.status_code, resp.content))

        result = resp.json()
        tools.clean_dict(result)
        if 'gw_err_resp' in result or not (result['code'] == 200 and result['success']):
            ##TODO need to notify admin
            raise Exception('Invalid Youzan Response: %s' %resp.content)

        return result

    def send_request(self, url, method, param_map, files):
        headers_map = {
            'User-Agent': 'X-YZ-Client 3.0.0 - Python',
            'Content-Type': 'application/json;charset=UTF-8'
        }

        req_data = json.dumps(param_map)
        if method.upper() == 'GET':
            return requests.get(url=url, data=req_data, headers=headers_map)

        elif method.upper() == 'POST':
            return requests.post(url=url, data=req_data, files=files, headers=headers_map)


