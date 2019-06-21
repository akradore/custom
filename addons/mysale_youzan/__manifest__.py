# -*- coding: utf-8 -*-
{
    'name': "mysale_youzan",

    'summary': """
        与有赞同步更新商品、订单、库存信息
        商品信息：odoo<=>有赞
        订单信息: 有赞=>odoo
        库存信息: odoo<=>有赞
        """,

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
    'depends': ['mysale_base'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/res_config_settings.xml',
        'views/cron_job.xml',
        'views/stock_synchron.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    'installable': True,
}
