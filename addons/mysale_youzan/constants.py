#[STOCK] 新增门店时，需要修改作业类型IDS
ZC2RS_WH_IN_PICKING_TYPE_IDS = (5,)   #总部统配门店仓对应的入库作业类型ID
PO2RS_WH_IN_PICKING_TYPE_IDS = (7,29) #采购直配门店仓对应的入库作业类型ID


#[EXTERNAL]
YOUZAN_CLIENT_ID = '7e9b3f9f5eb5406820'
YOUZAN_CLIENT_SECRET = '72c60b40e808e2e0eae7b26e2dd475ef'
YOUZAN_AUTHORITY_ID = '42971327'
YOUZAN_API_ADMIN_ID = '431154697'

YOUZAN_API_GETWAY = 'https://open.youzanyun.com/api'
YOUZAN_AUTHORIZE_URL = 'https://open.youzanyun.com/auth/token'

RETAIL_SOURCE = 'PRINCESS_MIA'
ORDER_FROM_YOUZAN_RETAIL = 'yz_retail'

YZAPI_SCOPE_REQUIRED = (
'multi_store', 'shop', 'item', 'trade', 'logistics', 'coupon_advanced', 'user', 'pay_qrcode', 'trade_virtual',
'reviews', 'item_category', 'storage', 'retail_goods', 'retail_product', 'retail_stock', 'retail_supplier',
'retail_store', 'retail_shop', 'retail_trade')

APPLY_ORDER_STATUS_MAP = {
    1: 'create',
    5: 'cancel',
    6: 'done',
    15: 'check',
}

"""
0:'默认值',
1:'微信自有支付',
2:'支付宝',
3:'银联银行卡',
4:'财付通银行卡',
5:'银行卡',
6:'找人代付',
7:'联动U付银行卡',
8:'货到付款',
9:'微信安全支付-代销',
10:'百度支付银行卡',
11:'合并付货款',
12:'领取赠品',
13:'优惠兑换',
14:'自动付货款',
15:'爱学贷',
16:'微信红包支付',
17:'返利',
18:'ump红包',
19:'payza支付',
20:'易宝支付银行卡',
21:'paypal',
22:'qq支付',
23:'有赞E卡-代销',
24:'储值余额付款',
25:'礼品卡支付',
26:'分销商余额支付',
27:'信用卡银联支付',
28:'储蓄卡银联支付',
29:'代收账户',
30:'储值账户',
31:'保证金账户',
32:'收款码',
33:'微信',
34:'刷卡',
35:'二维码台卡',
36:'储值卡',
37:'有赞E卡',
38:'标记收款-自有微信支付',
39:'标记收款-自有支付宝',
40:'标记收款-自有POS刷卡',
41:'通联刷卡支付',
42:'记账账户',
43:'现金支付',
44:'组合支付',
"""
PAYWAY_TO_JOURNAL_MAP = {
    0: 'CSH1',  # '默认值',
    1: 'WEIIN',  # '微信自有支付',
    2: 'ZFB',  # '支付宝',
    43: 'CASH',  # ''现金支付',
}
