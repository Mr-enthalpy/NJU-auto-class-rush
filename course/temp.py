from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


GROUP_TO_KIND = {
    "ZY": "1",
    "TY": "2",
    "GG06": "3",
    "GG01": "4",
    "MY": "5",
    "GG02": "6,7",
    "YD": "8",
    "KZY": "12",
    "TX01": "13",
    "TX02": "14",
    "TX03": "15",
    "TX04": "16",
}
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent


def _text(row, selector: str) -> str:
    cell = row.select_one(selector)
    return cell.get_text(" ", strip=True) if cell else ""


def parse_course_files(course_dir: Path) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for group, course_kind in GROUP_TO_KIND.items():
        html_path = course_dir / f"{group}.html"
        if not html_path.exists():
            continue
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
        for row in soup.select("tr.course-tr"):
            number_tag = row.select_one("a.cv-jxb-detail")
            if number_tag is None:
                continue
            number = number_tag.get("data-number") or number_tag.get("data-course-number")
            teaching_class_id = number_tag.get("data-teachingclassid") or number_tag.get(
                "data-teaching-class-id"
            )
            if not number or not teaching_class_id:
                continue
            course = {
                "teachingClassId": teaching_class_id,
                "courseKind": course_kind,
                "teachingClassType": group,
                "detail": _text(row, "td.sjdd"),
                "name": _text(row, "td.kcmc"),
                "location": _text(row, "td.xq"),
            }
            grouped.setdefault(number, []).append(course)

    return {
        number: items[0] if len(items) == 1 else items
        for number, items in grouped.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="将选课网页 HTML 快照转换为课程索引")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "new_courses.json",
        help="输出 JSON 路径，默认写入 new_courses.json",
    )
    args = parser.parse_args()
    catalog = parse_course_files(HERE)
    args.output.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )
    print(f"已生成 {len(catalog)} 个课程号：{args.output}")


if __name__ == "__main__":
    main()
