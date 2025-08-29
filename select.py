import base64
import copy
import json
import time
import itertools

from Crypto.Cipher import AES
from rich.console import Console
from rich.live import Live
from rich.table import Table


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
    console = Console()
    stat = [True for _ in range(len(clist))]
    msg_list = ["等待中..." for _ in range(len(clist))]

    spinner = itertools.cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])

    def build_table(flash_icon=""):
        table = Table(title="选课状态监视器", show_lines=True)
        table.add_column("课程ID", justify="center")
        table.add_column("状态", justify="left")
        for cid, msg in zip(idlist, msg_list):
            table.add_row(cid, msg)
        return table

    with Live(build_table(), refresh_per_second=10, console=console) as live:
        while any(stat):
            flash = next(spinner)  # 当前帧字符
            for i, course in enumerate(clist):
                if not stat[i]:
                    continue
                try:
                    status = _select(session, course).json()
                    time.sleep(W_TIME)
                    msg = status.get("msg", "未知状态")
                except:
                    msg = "网络异常，重试中..."
                if msg == "非法请求":
                    msg = "登录失效，正在重登..."
                    session = re_login()
                elif status.get("code") == "1" or msg == "请按顺序选课":
                    try:
                        _check(session, course, xh)
                    except:
                        pass
                    stat[i] = False
                    msg = "✅ 抢课成功"
                else:
                    # 添加闪动符号
                    msg = f"{flash} 正在尝试：{msg}"

                msg_list[i] = msg
            live.update(build_table())



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