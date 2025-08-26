from typing import final

from des import get_hash
from login import login
from select import watch
import json

if __name__ == "__main__":
    with open('courses.json', 'r') as f:
        all_courses = json.load(f)
    print('下面请输入你想要抢的课程，每输完一个按回车，输入exit退出')
    Class_list: list[dict] = []
    while True:
        class_id = input("课程号: ").strip()
        if class_id == 'exit':
            break
        if class_id not in all_courses:
            print("课程号不存在，请重新输入")
            continue
        Class_list.append(all_courses[class_id])

    print('输入你的学号，密码')
    XH = input("学号: ").strip()
    RAW_PWD = input("密码: ").strip()
    with open('config.json', 'r') as f:
        config = json.load(f)
    KEYS = config['HASH_KEY']
    PWD = get_hash(RAW_PWD, KEYS)
    AGENT = config['AGENT']
    session, XKLCDM = login(XH, RAW_PWD, AGENT)

    final_class_list = [{**{"operationType":"1","studentCode":XH,"electiveBatchCode":XKLCDM}, **course} for course in Class_list]
    # {"data":{"operationType":"1","studentCode":"221180004","electiveBatchCode":"64a7896404fa4856acb78e45e2594457","teachingClassId":"2025202610037243001","courseKind":"6,7","teachingClassType":"GG02"}}
    watch(Class_list, session, XH)