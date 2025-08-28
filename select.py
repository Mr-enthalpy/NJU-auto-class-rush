import base64
import copy
import json
import random
import time

from Crypto.Cipher import AES


def _pad_pkcs7(data: bytes) -> bytes:
    pad_len = 16 - (len(data) % 16)
    return data + bytes([pad_len] * pad_len)

def _encrypt_add_param(raw_data: dict) -> str:
    with open('config.json', 'r') as f:
        config = json.load(f)
    AES_KEY = config['AES_KEY'].encode("utf-8")
    # step1: 转换为 JSON 字符串
    data_str = json.dumps({"data": raw_data}, separators=(",", ":"))

    # step2: 拼接时间戳（JavaScript 的 Date.parse(new Date())）
    timestamp = str(int(time.time() * 1000))  # JS timestamp in milliseconds
    full_str = data_str + "?timestrap=" + timestamp
    full_bytes = full_str.encode("utf-8")

    # step3: PKCS7 padding + AES ECB
    padded = _pad_pkcs7(full_bytes)
    cipher = AES.new(AES_KEY, AES.MODE_ECB)
    encrypted = cipher.encrypt(padded)

    # step4: base64 编码输出
    return base64.b64encode(encrypted).decode("utf-8")

def _select(session, raw_param):
    encrypted = _encrypt_add_param(raw_param)
    return session.post(
        "https://xk.nju.edu.cn/xsxkapp/sys/xsxkapp/elective/volunteer.do",
        data={
            "addParam": encrypted,
            "studentCode": raw_param["studentCode"]
        }
    )


def _check(session, course, xh):
    res = session.post("https://xk.nju.edu.cn/xsxkapp/sys/xsxkapp/elective/studentstatus.do", data={"studentCode": xh, "teachingClassId": course["data"]["teachingClassId"], "type": "0"}, )
    return res

def watch(idlist, clist, session, xh, re_login):
    with open('config.json', 'r') as f:
        config = json.load(f)
    W_TIME = config['WAIT_TIME']
    stat = [True for _ in range(len(clist))]
    while any(stat):
        for i, course in enumerate(clist):
            if not stat[i]:
                print(f"Class {idlist[i]} Success!")
                continue
            try:
                status = _select(session, course).json()
                msg = status['msg']
                print(f'Class {idlist[i]} message: {msg}')
                time.sleep(W_TIME)
            except:
                continue
            msg = status['msg']
            if msg == "非法请求":
                print("Logged out, please try to resume...")
                session = re_login()
                continue
            if status["code"] == "1" or msg == "请按顺序选课":
                try:
                    _check(session, course, xh)
                except:
                    pass
                stat[i] = False
                print(f"Class {idlist[i]} Success!")


def select_from_alternative_list(clist, session, xh):
    U_TIME = 0.4
    clist = copy.deepcopy(clist)
    for course in clist:
        if clist == []:
            return False
        cnt = 0
        err = 0
        while 1:
            cnt += 1
            try:
                status = _select(session, course).json()
            except Exception as e:
                err += 1
                print(f"{err} err: {e}")
                continue
            msg = status['msg']
            print(f"{cnt}: {msg}")
            if msg == "当前时间不在选课开放时间范围内":
                time.sleep(U_TIME)
                continue
            if msg == "非法请求":
                print("Logged Out\nResuming...")
                return False
            if status["code"] == 1 or msg == "请按顺序选课":
                try:
                    _check(session, course, xh)
                except:
                    pass
                return True
            if msg == "该课程超过课容量" or status["extmsg"] == "已满" :
                clist = clist[1:]
            print(status)
    return False