import bs4
from bs4 import BeautifulSoup
import json

if __name__ == '__main__':
    TRANS = {"ZY": "1", "TY": "2", "GG01": "4", "GG02": "6,7", "GG06": '3', "YD": "8", "MY": "5", "KZY": "12", "TX01": "13", "TX02": "14", "TX03": "15", "TX04": "16"}
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
                div: bs4.Tag | None = row.find('td', class_='sjdd')
                name: str = row.find('td', class_='kcmc').get_text().strip()
                location : bs4.Tag | None = row.find('td', class_='xq')
                info = div.get_text().strip() if div is not None else ''
                loca = location.get_text().strip() if location else ''
                if number in result: # 说明是number相同，id不同的课程，存储为同number下的list
                    if isinstance(result[number], list):
                        result[number].append({
                            'teachingClassId': teachingclassid,
                            'courseKind': course_id,
                            'teachingClassType': group,
                            "detail": info,
                            "name": name,
                            "location": loca
                        })
                    else:
                        result[number] = [result[number], {
                            'teachingClassId': teachingclassid,
                            'courseKind': course_id,
                            'teachingClassType': group,
                            "detail": info,
                            "name": name,
                            "location": loca
                        }]
                else:
                    result[number] = {
                        'teachingClassId': teachingclassid,
                        'courseKind': course_id,
                        'teachingClassType': group,
                        "detail": info,
                        "name": name,
                        "location": loca
                    }
        except FileNotFoundError:
            print(f"File {group}.html not found. Skipping.")
            continue


    with open('../new_courses.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
