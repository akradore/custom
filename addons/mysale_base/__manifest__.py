# -*- coding: utf-8 -*-
{
    'name': "mysale_base",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['sale_management', 'stock', 'queue_job'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/res_group.xml',
        'views/res_config_settings.xml',
        'views/mysale_logistics.xml',
        'views/stock_picking.xml',
        'views/stock_synchron.xml',
        'views/menu.xml',
    ],

    'installable': True,
}
