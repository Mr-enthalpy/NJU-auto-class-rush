from des import get_hash
from login import login
from select import watch
import json

if __name__ == "__main__":
    print('输入你的学号，密码')
    XH = input("学号: ").strip()
    RAW_PWD = input("密码: ").strip()
    with open('config.json', 'r') as f:
        config = json.load(f)
    KEYS = config['HASH_KEY']
    PWD = get_hash(RAW_PWD, KEYS)
    AGENT = config['AGENT']
    session, XKLCDM = login(XH, RAW_PWD, AGENT)

    Class_list = [{"teachingClassId":"2025202610037243001","courseKind":"6,7","teachingClassType":"GG02"}, ]#示例
    # 打开选课界面，按下F12，在F12中选择网络（network），筛选项为XHR，然后不关闭F12打开的界面，对于想要抢的科目选择收藏，此时会在右侧监视到一个跳出来的favorite.io，
    # 点击该项，在右侧的标题栏中选择负载，在表单栏中可以看到一个addParam，复制该行中形如
    # "teachingClassId":"xxx","courseKind":"xxx","teachingClassType":"xxx"的部分内容，然后添加到粘贴到上面的Class_list中
    full_class_list = [{**{"operationType":"1","studentCode":XH,"electiveBatchCode":XKLCDM}, **course} for course in Class_list]
    watch(full_class_list, session, XH)