import json

from des import get_hash
from login import login
from select import watch

if __name__ == "__main__":
    with open('courses.json', 'r') as f:
        all_courses = json.load(f)
    print('下面请输入你想要抢的课程，每输完一个按回车，输入exit退出，输入load加载上次保存的学号密码和课程号')
    Class_list: list[dict] = []
    Class_id_list: list[str] = []
    load_flag: bool = False
    XH = ''
    RAW_PWD = ''
    while True:
        class_id = input("课程号: ").strip()
        if class_id == 'exit':
            break
        elif class_id == 'load':
            try:
                with open('user.json', 'r') as f:
                    user_data = json.load(f)
                Class_id_list = user_data['CLASS_ID_LIST']
                Class_list = [all_courses[cid] for cid in Class_id_list if cid in all_courses]
                XH = user_data['XH']
                RAW_PWD = user_data['RAW_PWD']
                print(f"已加载上次保存的课程号: {Class_id_list}")
                load_flag = True
            except Exception as e:
                print(f"加载失败: {e}")
            continue
        elif class_id not in all_courses:
            print("课程号不存在，请重新输入")
            continue
        elif class_id in Class_id_list:
            print("课程号已存在，请重新输入")
            continue
        Class_list.append(all_courses[class_id])
        Class_id_list.append(class_id)
    if not load_flag:
        print('输入你的学号，密码')
        XH = input("学号: ").strip()
        RAW_PWD = input("密码: ").strip()
    # 保存学号密码和课程号
    with open('user.json', 'w') as f:
        json.dump({
            'XH': XH,
            'RAW_PWD': RAW_PWD,
            'CLASS_ID_LIST': Class_id_list
        }, f, indent=4)
    with open('config.json', 'r') as f:
        config = json.load(f)
    KEYS = config['HASH_KEY']
    PWD = get_hash(RAW_PWD, KEYS)
    AGENT = config['AGENT']
    session, XKLCDM = login(XH, PWD, AGENT)
    def re_login():
        _session, _ = login(XH, PWD, AGENT)
        return _session
    final_class_list = [{**{"operationType":"1","studentCode":XH,"electiveBatchCode":XKLCDM}, **course} for course in Class_list]
    watch(Class_id_list, final_class_list, session, XH, re_login)