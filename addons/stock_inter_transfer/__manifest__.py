# -*- coding: utf-8 -*-
{
    'name': "库间调拨(支持一步调拨，两步调拨)",
    'description': """
====================================

库间调拨单
--------------------------------------------
应用场景及主要功能：
    * 仓库间调拨：将指定批次（或指定箱号）的货物从A仓库调拨到B仓库
    * 一步调拨，Odoo系统已经支持，但指定批次/箱号的操作界面不太友好
    * 两步调拨，A仓库做调出操作，B仓库做调入操作，Odoo不支持此功能
    * 本模块新增库间调拨单，调拨单上填写调出仓、调入仓，调拨类型（一步调拨，两步调拨），调拨明细（产品、批次、箱号、数量等）
    * 调拨单确认后，系统自动产生一步调拨单或两步调拨单
    
    """,

    'author': "OSCG",
    'website': "http://www.zhiyunerp.com",
    'category': 'Warehouse',
    'version': '0.1',
    'depends': [
       'stock',
       ],
    'data': [
        'views/stock_inter_views.xml',
        'views/stock_inter_sequence.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}