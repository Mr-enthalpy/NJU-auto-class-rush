from __future__ import annotations

import base64
from typing import Any

import cv2
import numpy as np
import requests

from auto_code import solve_query


BASE_URL = "https://xk.nju.edu.cn/xsxkapp"
REQUEST_TIMEOUT = 20


def extract_vcode_image(src: str) -> np.ndarray:
    _, b64_data = src.split(",", 1)
    img_bytes = base64.b64decode(b64_data)
    image = cv2.imdecode(np.frombuffer(img_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("验证码图片解码失败")
    return image


def get_captcha_and_token(session) -> tuple[np.ndarray, str, str]:
    response = session.post(
        f"{BASE_URL}/sys/xsxkapp/student/4/vcode.do",
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data") or {}
    image_data = data.get("vode") or data.get("codeImage")
    uuid = data.get("uuid")
    if not image_data or not uuid:
        raise ValueError(f"验证码接口返回字段不完整：{payload.get('msg', '未知错误')}")
    return extract_vcode_image(image_data), uuid, data.get("token") or "null"


def login(xh: str, pwd: str, agent: str, is_new_student: bool) -> tuple[requests.Session, str]:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": agent,
            "Referer": f"{BASE_URL}/sys/xsxkapp/*default/index.do",
            "Connection": "close",
            "X-Requested-With": "XMLHttpRequest",
        }
    )

    while True:
        try:
            image, uuid, vtoken = get_captcha_and_token(session)
            order = solve_query(image)
            verify_code = ",".join(f"{x}-{y}" for y, x in order)
            response = session.post(
                f"{BASE_URL}/sys/xsxkapp/student/check/login.do",
                data={
                    "loginName": xh,
                    "loginPwd": pwd,
                    "verifyCode": verify_code,
                    "vtoken": vtoken,
                    "uuid": uuid,
                },
                timeout=REQUEST_TIMEOUT,
            )
            payload = response.json()
            if str(payload.get("code")) == "1":
                print("✅ 登录成功")
                break
            print(f"⚠️ 登录失败，原因：{payload.get('msg', '未知错误')}，正在重试...")
        except Exception as exc:
            print(f"⚠️ 登录请求异常：{exc}，正在重试...")

    data = payload.get("data") or {}
    login_token = data.get("token")
    if not login_token:
        raise RuntimeError("登录成功但未返回会话令牌")
    session.headers.update({"token": login_token})

    batch_code = get_xklcdm(session, is_new_student)
    print(f"✅ 当前选课轮次为：{batch_code}")
    return session, batch_code


def _batch_code(batch: dict[str, Any]) -> str | None:
    value = batch.get("code") or batch.get("batchCode")
    return str(value) if value not in (None, "") else None


def _is_selectable(batch: dict[str, Any]) -> bool:
    value = batch.get("canSelect")
    return value in (True, 1, "1", "true", "True")


def _matches_student_type(batch: dict[str, Any], is_new_student: bool) -> bool:
    name = str(batch.get("name") or batch.get("batchName") or "")
    expected = "新生" if is_new_student else "老生"
    return expected in name


def get_xklcdm(session, is_new_student: bool = False) -> str:
    response = session.post(
        f"{BASE_URL}/sys/xsxkapp/elective/batch.do",
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    if str(payload.get("code")) != "1":
        raise RuntimeError(f"获取选课轮次失败：{payload.get('msg', '未知错误')}")

    batches = payload.get("dataList") or []
    typed = [batch for batch in batches if _matches_student_type(batch, is_new_student)]
    if typed:
        selectable = [batch for batch in typed if _is_selectable(batch)]
        chosen = (selectable or typed)[0]
    else:
        active = [batch for batch in batches if str(batch.get("active")) == "1"]
        selectable = [batch for batch in batches if _is_selectable(batch)]
        chosen = (active or selectable or batches)[0] if batches else None

    code = _batch_code(chosen) if chosen else None
    if not code:
        raise RuntimeError("未找到可用的选课轮次")
    return code
