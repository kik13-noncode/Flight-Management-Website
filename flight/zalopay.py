import time
import json
import hmac
import hashlib
import random
import urllib.request
import urllib.parse
from datetime import datetime

ZALOPAY_CONFIG = {
    "app_id": 553,
    "key1": "9phuAOYhan4urywHTh0ndEXiV3pKHr5Q",
    "endpoint": "https://sb-openapi.zalopay.vn/v2/create"
}


def create_zalopay_payment(amount, seat_id, app_user="OU_Airlines_User"):
    amount_int = int(float(amount or 0))
    trans_id = random.randrange(1000000)
    app_trans_id = "{:%y%m%d}_{}".format(datetime.today(), trans_id)
    app_time = int(round(time.time() * 1000))

    embed_data = json.dumps({
        "seat_id": str(seat_id)
    }, separators=(',', ':'))

    items = json.dumps([{
        "itemid": str(seat_id),
        "itemname": "Ve may bay OU Airlines",
        "itemprice": amount_int,
        "itemquantity": 1
    }], separators=(',', ':'))

    order = {
        "app_id": ZALOPAY_CONFIG["app_id"],
        "app_trans_id": app_trans_id,
        "app_user": str(app_user),
        "app_time": app_time,
        "embed_data": embed_data,
        "item": items,
        "amount": amount_int,
        "description": f"OU Airlines - Thanh toan ghe #{seat_id}",
        "bank_code": ""
    }

    data_str = "{}|{}|{}|{}|{}|{}|{}".format(
        order["app_id"],
        order["app_trans_id"],
        order["app_user"],
        order["amount"],
        order["app_time"],
        order["embed_data"],
        order["item"]
    )
    order["mac"] = hmac.new(
        ZALOPAY_CONFIG["key1"].strip().encode(),
        data_str.encode(),
        hashlib.sha256
    ).hexdigest()

    response = urllib.request.urlopen(
        url=ZALOPAY_CONFIG["endpoint"],
        data=urllib.parse.urlencode(order).encode()
    )
    res = json.loads(response.read().decode())
    res["app_trans_id"] = app_trans_id
    print("ZaloPay Response:", res)
    return res


def query_zalopay_order(app_trans_id):
    data_str = f"{ZALOPAY_CONFIG['app_id']}|{app_trans_id}|{ZALOPAY_CONFIG['key1']}"
    mac = hmac.new(
        ZALOPAY_CONFIG["key1"].strip().encode(),
        data_str.encode(),
        hashlib.sha256
    ).hexdigest()

    params = {
        "app_id": ZALOPAY_CONFIG["app_id"],
        "app_trans_id": app_trans_id,
        "mac": mac
    }

    response = urllib.request.urlopen(
        url="https://sb-openapi.zalopay.vn/v2/query",
        data=urllib.parse.urlencode(params).encode()
    )
    return json.loads(response.read().decode())