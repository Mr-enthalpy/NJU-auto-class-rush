from bs4 import BeautifulSoup
import json

TRANS = {"ZY": "1", "TY": "2", "GG01": "4", "GG02": "6,7", "GG06": '3', "YD": "8", "KZY": "12", "TX01": "13", "TX02": "14", "TX03": "15", "TX04": "16"}
result = {}

for group, course_id in TRANS.items():
    # 读取 HTML 文件
    try:
        with open(group + '.html', 'r', encoding='utf-8') as file:
            html = file.read()
        # 使用 BeautifulSoup 解析
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.select('tr.course-tr')
        for row in rows:
            number_tag = row.select_one('a.cv-jxb-detail')
            if not number_tag:
                continue
            number = number_tag['data-number']
            teachingclassid = number_tag['data-teachingclassid']

            result[number] = {
                'teachingclassid': teachingclassid,
                'courseKind': course_id,
                'teachingClassType': group
            }
    except FileNotFoundError:
        print(f"File {group}.html not found. Skipping.")
        continue


with open('courses.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=4)
