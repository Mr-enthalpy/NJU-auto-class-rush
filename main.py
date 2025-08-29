import json

from des import get_hash
from login import login
from select import watch

if __name__ == "__main__":
    with open('courses.json', 'r') as f:
        all_courses = json.load(f)
    print('欢迎使用自动选课程序！')
    print('是否加载上次抢课时使用的学号密码？(Y/N)')
    Class_list: list[dict] = []
    Class_id_list: list[str] = []
    XH = ''
    RAW_PWD = ''
    load_flag: bool = False
    while True:
        choice: str= input().strip().upper()
        if choice in ['Y', 'N']:
            if choice == 'Y':
                try:
                    with open('user.json', 'r') as f:
                        user_data = json.load(f)
                    XH = user_data['XH']
                    RAW_PWD = user_data['RAW_PWD']
                    print(f"已加载上次保存的学号密码")
                    load_flag = True
                except Exception as e:
                    print(f"加载失败: {e}")
                break
            elif choice == 'N':
                break
            else:
                print('输入有误，请重新输入(Y/N)')
    print('指令提示：')
    print('输入add class_id1 class_id2 ...以添加课程号\n'
          '输入del class_id1 class_id2 ...以删除课程号\n'
          '输入load加载上次课程号到列表中\n'
          '输入clear清除当前课程号列表\n'
          '输入show以查看当前课程号\n'
          '输入exit退出添加课程号环\n'
          '输入help以查看帮助。')
    save_Class_id_list = None
    while True:
        command = input(">>> ").strip().lower()
        if command == 'exit':
            break
        elif command == 'help':
            print('输入add class_id1 class_id2 ...以添加课程号\n'
                  '输入del class_id1 class_id2 ...以删除课程号\n'
                  '输入load加载上次课程号到列表中\n'
                  '输入clear清除当前课程号列表\n'
                  '输入show以查看当前课程号\n'
                  '输入exit退出添加课程号环\n'
                  '输入help以查看帮助。')
        elif command == 'show':
            print(f"当前课程号: {Class_id_list}")
        elif command.startswith('add '):
            class_ids = command[4:].strip().split()
            for class_id in class_ids:
                if class_id in all_courses:
                    if class_id not in Class_id_list:
                        Class_list.append(all_courses[class_id])
                        Class_id_list.append(class_id)
                    else:
                        print(f"待添加课程号 {class_id} 非法")
                else:
                    print(f"课程号 {class_id} 不存在")
        elif command == 'load':
            try:
                if save_Class_id_list is None:
                    with open('user.json', 'r') as f:
                        user_data = json.load(f)
                    save_Class_id_list = user_data['CLASS_ID_LIST']
                load_class_id_list = [cid for cid in save_Class_id_list if cid in all_courses and cid not in Class_id_list]
                load_Class_list = [all_courses[cid] for cid in load_class_id_list]
                Class_id_list += load_class_id_list
                Class_list += load_Class_list
                print(f"已加载上次保存的课程号: {load_class_id_list}")
            except Exception as e:
                print(f"加载失败: {e}")
        elif command.startswith('del '):
            class_ids = command[4:].strip().split()
            for class_id in class_ids:
                if class_id in all_courses:
                    if class_id in Class_id_list:
                        idx = Class_id_list.index(class_id)
                        Class_id_list.pop(idx)
                        Class_list.pop(idx)
                    else:
                        print(f"待删除课程号 {class_id} 不存在")
                else:
                    print(f"课程号 {class_id} 非法")
        elif command == 'clear':
            Class_id_list = []
            Class_list = []
        else:
            print('输入有误，请重新输入(help以查看帮助)')
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