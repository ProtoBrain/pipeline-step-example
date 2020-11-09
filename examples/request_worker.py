#!/usr/bin/python3
import requests
import json
import os
from enum import Enum

cdir = os.path.dirname(os.path.abspath(__file__))

class ReqType(Enum):
    GET = 0
    POST = 1
    PUT = 2
    HEAD = 3

API_URL = "https://api.protobrain.io/api/v1/"
PB_HEADERS = dict()

def request(url, type, values = {}):
    
    _url = API_URL + url
    _headers = PB_HEADERS
    reqtype = type.name
    
    print("INFO", "REQUEST:\n    Type: {}\n    Url: {}".format(reqtype, _url,))
    
    if len(values) > 0:
        resp =  requests.request(method = reqtype, headers = _headers, url = _url, data = json.dumps(values))
    else:
        resp =  requests.request(method = reqtype, headers = _headers, url = _url)

    if resp.status_code >= 400 or "error" in resp.json():
            try:
                print("ERROR REQUEST", "\n    STATUS: " + str(resp.status_code), f"\n    Values: {json.dumps(values, indent = 4)}")
                print(f"RESPONSE INFO: {json.dumps(resp.json(), indent=4)}")
            except:
                pass
            
            exit(0)

    return resp


def create_data_layer(actId, comment):
    values = {
    "type": "label",
    "subtype": "scene",
    "act_id": actId,
    "color": "#d7d7d7",
    "comment": f"{comment}",
    "is_private": False
    }

    cdl_url = f'fire/act/{actId}/data_layer'
    resp = request(url = cdl_url, type = ReqType.POST, values = values).json()

    return int(resp["id"])


def create_scene(datalayerId, comment, sbeg, send, color):
 
    dur = int(float(send) - float(sbeg))
    if dur < 1:
        dur = 1
        
    values = \
        {
            "data_layer_id": datalayerId,
            "position": int(float(sbeg)),
            "length": dur,
            "comment": f"{comment}",
            "color": f"{color}",
            "is_private": False
        }
 
    cs_url = 'fire/label/scene'

    request(url = cs_url, type = ReqType.POST, values = values)