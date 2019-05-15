# -*- coding: utf-8 -*-
from odoo import http

# class MysaleBase(http.Controller):
#     @http.route('/mysale_base/mysale_base/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mysale_base/mysale_base/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('mysale_base.listing', {
#             'root': '/mysale_base/mysale_base',
#             'objects': http.request.env['mysale_base.mysale_base'].search([]),
#         })

#     @http.route('/mysale_base/mysale_base/objects/<model("mysale_base.mysale_base"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mysale_base.object', {
#             'object': obj
#         })