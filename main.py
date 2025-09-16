import json

from des import get_hash
from login import login
from select import watch

if __name__ == "__main__":
    print('欢迎使用自动选课程序！')
    print('是否加载上次抢课时使用的学号密码和选课批次设置？(Y/N)')
    Class_list: dict[str, list[dict]|dict] = {}
    XH = ''
    RAW_PWD = ''
    load_flag: bool = False
    student_code = False
    with open('courses.json', 'r' , encoding='utf-8') as f:
        all_courses = json.load(f)
    while True:
        choice: str= input().strip().upper()
        if choice in ['Y', 'N']:
            if choice == 'Y':
                try:
                    with open('user.json', 'r') as f:
                        user_data = json.load(f)
                    XH = user_data['XH']
                    RAW_PWD = user_data['RAW_PWD']
                    student_code = user_data['student_code']
                    print(f"已加载上次保存的学号密码和选课批次设置")
                    if student_code:
                        with open('new_courses.json', 'r', encoding='utf-8') as f:
                            all_courses = json.load(f)
                    load_flag = True
                except Exception as e:
                    print(f"加载失败: {e}")
                break
            elif choice == 'N':
                print('请手动输入学号密码和选课批次设置')
                c = input(f"你是否是新生？(Y/N)").strip().upper()
                if c == 'Y':
                    with open('new_courses.json', 'r', encoding='utf-8') as f:
                        all_courses = json.load(f)
                    student_code = True
                break
            else:
                print('输入有误，请重新输入(Y/N)')
    print('指令提示：')
    print('输入add class_id1 class_id2 ...以添加课程号\n'
          '输入del class_id1 class_id2 ...以删除课程号\n'
          '输入detail class_id1 class_id2 ...以查看课程详情\n'
          '输入load加载上次课程号到列表中\n'
          '输入clear清除当前课程号列表\n'
          '输入show以查看当前课程号\n'
          '输入exit退出添加课程号环\n'
          '输入help以查看帮助。')
    save_Class_id_list = None
    while True:
        command = input(">>> ").strip()
        if command == 'exit':
            break
        elif command == 'help':
            print('输入add class_id1 class_id2 ...以添加课程号\n'
                  '输入del class_id1 class_id2 ...以删除课程号\n'
                  '输入detail class_id1 class_id2 ...以查看课程详情\n'
                  '输入load加载上次课程号到列表中\n'
                  '输入clear清除当前课程号列表\n'
                  '输入show以查看当前课程号\n'
                  '输入exit退出添加课程号环\n'
                  '输入help以查看帮助。')
        elif command == 'show':
            for class_id in Class_list:
                course = Class_list[class_id]
                match course:
                    case list():
                        for c in course:
                            print(f"课程ID{class_id},  课程名: {c['name']}, 课程信息: {c['detail']}, 上课地点: {c['location']}")
                    case dict():
                        print(f"课程ID{class_id},  课程名: {course['name']}, 课程信息: {course['detail']}, 上课地点: {course['location']}")
        elif command.startswith('add '):
            class_ids = command[4:].strip().split()
            for class_id in class_ids:
                if class_id in all_courses:
                    course = all_courses[class_id]
                    match course:
                        case list():
                            print("该课程号下有多个教学班，请输入具体教学班号以区分:")
                            for idx, c in enumerate(course):
                                print(f"  教学班 {idx+1}：{c["name"]}, {c["detail"]}, {c["location"]}")
                            teaching_class_inputs = input("请输入教学班号: ").strip().split() # 用户输入具体教学班号，即idx
                            for teaching_class_input in teaching_class_inputs:
                                try:
                                    teaching_class_index = int(teaching_class_input) - 1
                                    if 0 <= teaching_class_index < len(course):
                                        selected_course = course[teaching_class_index]
                                        if class_id not in Class_list:
                                            Class_list[class_id] = selected_course
                                        else:
                                            match Class_list[class_id]:
                                                case list():
                                                    if selected_course not in Class_list[class_id]:
                                                        Class_list[class_id].append(selected_course)
                                                case dict():
                                                    if Class_list[class_id] != selected_course:
                                                        Class_list[class_id] = [Class_list[class_id], selected_course]
                                    else:
                                        print("输入的教学班号无效，请重新添加该课程号。")
                                except ValueError:
                                    print("输入的教学班号无效，请重新添加该课程号。")
                        case dict():
                            Class_list[class_id] = course
                else:
                    print(f"课程号 {class_id} 不存在")
        elif command == 'load':
            try:
                if save_Class_id_list is None:
                    with open('user.json', 'r') as f:
                        user_data = json.load(f)
                    save_Class_id_list = user_data['CLASS_INFO']
                for class_id in save_Class_id_list:
                    class_info = Class_list[class_id]
                    if class_id in Class_list:
                        match Class_list[class_id]:
                            case list():
                                if class_info not in Class_list[class_id]:
                                    Class_list[class_id].append(class_info)
                            case dict():
                                if Class_list[class_id] != class_info:
                                    Class_list[class_id] = [Class_list[class_id], class_info]
                    else:
                        Class_list[class_id] = class_info
                print("已加载上次保存的课程号到当前列表中")
            except Exception as e:
                print(f"加载失败: {e}")
        elif command.startswith('del '):
            class_ids = command[4:].strip().split()
            for class_id in class_ids:
                if class_id in all_courses:
                    if class_id in Class_list:
                        match Class_list[class_id]:
                            case list():
                                print("该课程号下有多个教学班，请输入具体教学班号以区分:")
                                for idx, c in enumerate(Class_list[class_id]):
                                    print(f"  教学班 {idx+1}：{c["name"]}, {c["detail"]}, {c["location"]}")
                                teaching_class_inputs = input("请输入教学班号(输入all删除全部教学班): ").strip().split()
                                if 'all' in teaching_class_inputs:
                                    del Class_list[class_id]
                                    print(f"已删除课程号 {class_id} 下的所有教学班")
                                else:
                                    to_delete = []
                                    for teaching_class_input in teaching_class_inputs:
                                        try:
                                            teaching_class_index = int(teaching_class_input) - 1
                                            if 0 <= teaching_class_index < len(Class_list[class_id]):
                                                to_delete.append(teaching_class_index)
                                            else:
                                                print(f"输入的教学班号 {teaching_class_input} 无效，跳过")
                                        except ValueError:
                                            print(f"输入的教学班号 {teaching_class_input} 无效，跳过")
                                    for index in sorted(to_delete, reverse=True):
                                        del Class_list[class_id][index]
                                    if not Class_list[class_id]:
                                        del Class_list[class_id]
                                    print(f"已删除课程号 {class_id} 下的指定教学班")
                            case dict():
                                del Class_list[class_id]
                                print(f"已删除课程号 {class_id}")
                    else:
                        print(f"待删除课程号 {class_id} 不存在")
                else:
                    print(f"课程号 {class_id} 非法")
        elif command.startswith('detail '):
            class_ids = command[7:].strip().split()
            for class_id in class_ids:
                if class_id in all_courses:
                    course = all_courses[class_id]
                    if isinstance(course, list):
                        print(f"课程号 {class_id} 详情(存在多个教学班):")
                        for idx, c in enumerate(course):
                                print(f"  教学班 {idx + 1}：{c["name"]}, {c["detail"]}, {c["location"]}")
                    else:
                        print(f"课程号 {class_id} 详情:")
                        for k, v in course.items():
                            print(f"  {k}: {v}")
        elif command == 'clear':
            Class_list = {}
        else:
            print('输入有误，请重新输入(help以查看帮助)')
    if not load_flag:
        print('输入你的学号，密码')
        XH = input("学号: ").strip()
        RAW_PWD = input("密码: ").strip()
    use_ful_info: list[dict] = []
    Class_id_list: list[str] = []
    for class_id, class_info in Class_list.items():
        match class_info:
            case list():
                for c in class_info:
                    data = {"teachingClassId": c['teachingClassId'],
                                "courseKind": c['courseKind'],
                                "teachingClassType": c['teachingClassType']}
                    use_ful_info.append(data)
                    Class_id_list.append(c["name"])
            case dict():
                data = {"teachingClassId": class_info['teachingClassId'],
                            "courseKind": class_info['courseKind'],
                            "teachingClassType": class_info['teachingClassType']}
                use_ful_info.append(data)
                Class_id_list.append(class_info["name"])
    # 保存学号密码和课程号
    with open('user.json', 'w') as f:
        json.dump({
            'XH': XH,
            'RAW_PWD': RAW_PWD,
            'CLASS_INFO': Class_list,
            'student_code': student_code
        }, f, indent=4)
    with open('config.json', 'r') as f:
        config = json.load(f)
    KEYS = config['HASH_KEY']
    PWD = get_hash(RAW_PWD, KEYS)
    AGENT = config['AGENT']
    session, XKLCDM = login(XH, PWD, AGENT, student_code)
    def re_login():
        _session, _ = login(XH, PWD, AGENT, student_code)
        return _session
    final_class_list = [{**{"operationType":"1","studentCode":XH,"electiveBatchCode":XKLCDM}, **course} for course in use_ful_info]
    watch(Class_id_list, final_class_list, session, XH, re_login)