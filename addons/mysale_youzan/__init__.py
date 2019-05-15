# -*- coding: utf-8 -*-
"""
Youzan Retail:
1, message notify api auth='public', need to set default dbname param to odoo-server.conf;
[options]
db_name = euho_erptest
2, override the default behaive or http.route, Root
"""
from . import controllers
from . import models
from . import constants
