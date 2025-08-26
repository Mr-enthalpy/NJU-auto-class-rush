import requests
import json
from playwright.sync_api import sync_playwright


def login(xh, raw_pwd, agent):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://xk.nju.edu.cn/xsxkapp/sys/xsxkapp/*default/index.do")

        # 自动填账号密码（也可以交由你自己填写）
        page.fill("#loginName", xh)
        page.fill("#loginPwd", raw_pwd)

        print("🧠 请手动填写验证码并点击登录，完成后回到终端按下回车")
        input()

        page.wait_for_load_state("networkidle")
        cookies = context.cookies()

        # 提取 token：页面 localStorage 或 cookie 可能存有 login_token
        login_token = page.evaluate("localStorage.getItem('token')")
        if not login_token:
            login_token = page.evaluate("sessionStorage.getItem('token')")

        if not login_token:
            print("⚠️ 未能提取 login_token，请检查页面结构")
            browser.close()
            raise Exception("登录失败")

        print("✅ 登录成功，提取 cookies + token")

        # 注入 requests.Session
        session = requests.Session()
        session.headers.update({
            "User-Agent": agent,
            "Referer": "https://xk.nju.edu.cn/xsxkapp/sys/xsxkapp/*default/index.do",
            "token": login_token,
        })

        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
        xklcdm = login_and_get_batch_info(page)
        # 可选：测试一次是否真的登录成功
        res = session.post("https://xk.nju.edu.cn/xsxkapp/sys/xsxkapp/student/xkxf.do", data={"xh": xh, "xklcdm": xklcdm}).json()
        print(res.get("msg", "登录状态测试完成"))

        browser.close()
        return session, xklcdm

def login_and_get_batch_info(page):
    # 页面登录完成后，提取 sessionStorage 内容
    current_batch_json = page.evaluate("sessionStorage.getItem('currentBatch')")

    current_batch = json.loads(current_batch_json)

    xklcdm = current_batch["code"]
    can_select = current_batch["canSelect"]

    if can_select != "1":
        raise Exception(f"当前选课轮次 {xklcdm} 不处于开放状态")

    return xklcdm