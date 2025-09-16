import base64
import json
import re
import time

import cv2
import numpy as np
import requests

from auto_code import solve_query


def extract_vcode_image(src: str) -> np.ndarray:
    header, b64_data = src.split(",", 1)
    img_bytes = base64.b64decode(b64_data)

    # 解码为图像（OpenCV 格式：BGR ndarray）
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)  # shape: (H, W, 3)

    if img is None:
        raise ValueError("图像解码失败：检查 base64 格式是否正确")

    return img  # 返回 OpenCV 图像格式

def get_captcha_and_token(session) -> tuple[np.ndarray, str]:
    resp = session.post("https://xk.nju.edu.cn/xsxkapp/sys/xsxkapp/student/4/vcode.do")
    data = resp.json()["data"]
    img = extract_vcode_image(data["vode"])
    uuid = data["uuid"]
    return img, uuid


def login(xh: str, pwd: str, agent: str, code: bool) -> tuple[requests.Session, str]:
    """
    :param xh: 学号
    :param pwd: 密码（已加密）
    :param agent: User-Agent
    :param solve_query: 验证码图像识别函数，输入 bytes -> 输出 [(x1, y1), (x2, y2), ...]
    :return: (已登录的 session, xklcdm)
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": agent,
        "Referer": "https://xk.nju.edu.cn/xsxkapp/sys/xsxkapp/*default/index.do",
        "Connection": "close",  # 避免连接复用触发底层奇怪状态
    })
    while True:
        try:
            img, uuid = get_captcha_and_token(session)
            order = solve_query(img)
            code_str = ",".join([f"{y}-{x}" for x, y in order])
            payload = {
                "loginName": xh,
                "loginPwd": pwd,
                "verifyCode": code_str,
                "vtoken": "null",
                "uuid": uuid
            }

            resp = session.post("https://xk.nju.edu.cn/xsxkapp/sys/xsxkapp/student/check/login.do", data=payload)
            res = resp.json()
            if res.get("code") == '1':
                print("✅ 登录成功")
                break
            else:
                print(f"⚠️ 登录失败，原因：{res.get('msg', '未知错误')}，正在重试...")
                continue
        except Exception as e:
            print(f"⚠️ 发生异常：{e}，正在重试...")

    login_token = res["data"]["token"]

    # 更新 session headers 添加 token
    session.headers.update({
        "token": login_token
    })

    xklcdm = get_xklcdm(session, code)

    print(f"✅ 当前选课轮次为：{xklcdm}")
    return session, xklcdm


def get_xklcdm(session, code = False) -> str:
    url = "https://xk.nju.edu.cn/xsxkapp/sys/xsxkapp/elective/batch.do"
    resp = session.post(url)
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != "1":
        raise Exception("获取 batch 信息失败")

    # for batch in data.get("dataList", []):
    #     return batch["code"]
    # code 为True表示新生，选择第二个。
    if code:
        if len(data.get("dataList", [])) >= 2:
            return data["dataList"][1]["code"]
    else:
        if len(data.get("dataList", [])) >= 1:
            return data["dataList"][0]["code"]

    raise Exception("未找到可选的选课轮次")