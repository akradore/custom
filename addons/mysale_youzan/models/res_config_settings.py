# -*- coding: utf-8 -*-
# 1 : imports of python lib
import datetime

# 2 : imports of odoo
from odoo import _, api, exceptions, fields, models  # alphabetically ordered

# 3 : imports from odoo modules

# 4 : variable declarations


# Class
class YouzanRetailResConfigSettings(models.TransientModel):
    # Private attributes
    _inherit = 'res.config.settings'

    # Default methods

    # Fields declaration
    mysale_youzan_is_debug_mode = fields.Boolean(
        string="mysale youzan push message debug mode",
    )

    mysale_youzan_retail_order_last_update = fields.Datetime(
        "Last Update Date",
        default=fields.Datetime.now,
        help="Youzan Retail order last update datetime"
    )

    mysale_youzan_access_token = fields.Char(
        "Youzan AccessToken",
        help="Youzan Api AccessToken"
    )

    # Compute and search fields, in the same order of fields declaration

    # Constraints and onchanges

    # CRUD methods (and name_get, name_search, ...) overrides

    # Action methods

    # Business methods
    @api.multi
    def get_values(self):
        res = super(YouzanRetailResConfigSettings, self).get_values()
        res.update(
            mysale_youzan_is_debug_mode=self.env['ir.config_parameter'].sudo().get_param(
                'mysale_youzan.mysale_youzan_is_debug_mode'),
            mysale_youzan_retail_order_last_update=self.env['ir.config_parameter'].sudo().get_param(
                'mysale_youzan.mysale_youzan_retail_order_last_update'),
            mysale_youzan_access_token=self.env['ir.config_parameter'].sudo().get_param(
                'mysale_youzan.mysale_youzan_access_token')
        )
        return res

    def set_values(self):
        super(YouzanRetailResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('mysale_youzan.mysale_youzan_is_debug_mode',
                                                         self.mysale_youzan_is_debug_mode)

        self.env['ir.config_parameter'].sudo().set_param('mysale_youzan.mysale_youzan_access_tokens',
                                                         self.mysale_youzan_access_token)

        if not self.mysale_youzan_retail_order_last_update:
            self.mysale_youzan_retail_order_last_update = datetime.datetime.now() - datetime.timedelta(days=1)
        self.env['ir.config_parameter'].sudo().set_param('mysale_youzan.mysale_youzan_retail_order_last_update',
                                                         self.mysale_youzan_retail_order_last_update)


    @api.model
    def get_youzan_access_token(self, force_update=False):
        token = self.env['ir.config_parameter'].sudo().get_param(
            'mysale_youzan.mysale_youzan_access_token')

        if (not token) or force_update:
            from ..yzsdk import  Token
            token_generator = Token.DEFAULT_SETUP_TOKEN()
            token = token_generator.get_token()

            self.env['ir.config_parameter'].sudo().set_param(
                'mysale_youzan.mysale_youzan_access_token', token)

        return token

    @api.model
    def cron_refresh_youzan_access_token(self):
        # force update youzan access_token
        self.get_youzan_access_token(force_update=True)