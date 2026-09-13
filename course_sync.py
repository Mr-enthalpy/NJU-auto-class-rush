"""从当前选课轮次同步课程目录。

选课网页每学期都会更换教学班号，因此本地 JSON 只作为离线兜底，
实际运行时优先从已登录的选课会话读取最新目录。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


BASE_URL = "https://xk.nju.edu.cn/xsxkapp"
COURSE_TYPE_TO_KIND = {
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
COURSE_TYPE_TO_ENDPOINT = {
    "ZY": "elective/course.do",
    "TY": "elective/publicCourse.do",
    "GG01": "elective/publicCourse.do",
    "GG02": "elective/publicCourse.do",
    "GG06": "elective/publicCourse.do",
    "YD": "elective/publicCourse.do",
    "MY": "elective/publicCourse.do",
    "KZY": "elective/programCourse.do",
    "TX01": "elective/course.do",
    "TX02": "elective/course.do",
    "TX03": "elective/course.do",
    "TX04": "elective/course.do",
}
DEFAULT_COURSE_TYPES = tuple(COURSE_TYPE_TO_KIND)


def _normal_key(key: Any) -> str:
    return "".join(ch for ch in str(key).lower() if ch.isalnum())


def _pick(row: dict[str, Any], *names: str) -> Any:
    values = {_normal_key(key): value for key, value in row.items()}
    for name in names:
        value = values.get(_normal_key(name))
        if value not in (None, ""):
            return value
    return None


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "\n".join(filter(None, (_as_text(item) for item in value)))
    if isinstance(value, dict):
        for key in ("text", "name", "value", "content"):
            if key in value:
                return _as_text(value[key])
        return ""
    return str(value).strip()


def _iter_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_dicts(child)


def _course_from_row(row: dict[str, Any], group: str) -> dict[str, str] | None:
    teaching_class_id = _pick(
        row,
        "teachingClassId",
        "teachingclassid",
        "teachingClassID",
        "tcid",
        "jxbid",
    )
    number = _pick(row, "number", "courseNumber", "courseCode", "KCH", "data-number")
    if teaching_class_id is None or number is None:
        return None

    name = _as_text(_pick(row, "name", "courseName", "KCMC"))
    detail = _as_text(
        _pick(row, "detail", "schedule", "teachingTime", "classTime", "SJDD")
    )
    location = _as_text(_pick(row, "location", "campus", "XQ"))
    course_kind = _as_text(
        _pick(row, "courseKind", "courseKindCode", "courseTypeCode")
    ) or COURSE_TYPE_TO_KIND[group]
    teaching_class_type = _as_text(
        _pick(row, "teachingClassType", "teachingclasstype")
    ) or group
    return {
        "teachingClassId": _as_text(teaching_class_id),
        "courseKind": course_kind,
        "teachingClassType": teaching_class_type,
        "detail": detail,
        "name": name,
        "location": location,
    }


def _payload(student_code: str, batch_code: str, group: str) -> dict[str, Any]:
    # 不同版本的页面对分页字段命名略有差异；服务端会忽略未使用的字段。
    return {
        "studentCode": student_code,
        "electiveBatchCode": batch_code,
        "teachingClassType": group,
        "pageNumber": 0,
        "currentPage": 1,
        "pageSize": 2000,
        "rows": 2000,
    }


def refresh_catalog(
    session,
    student_code: str,
    batch_code: str,
    *,
    course_types: Iterable[str] = DEFAULT_COURSE_TYPES,
    base_url: str = BASE_URL,
) -> dict[str, dict[str, str] | list[dict[str, str]]]:
    """从当前选课批次读取课程，并转换为项目原有 JSON 格式。"""

    result: dict[str, list[dict[str, str]]] = {}
    seen: set[tuple[str, str]] = set()
    errors: list[str] = []

    for group in course_types:
        endpoint = COURSE_TYPE_TO_ENDPOINT.get(group)
        if endpoint is None:
            continue
        try:
            response = session.post(
                f"{base_url}/sys/xsxkapp/{endpoint}",
                data=_payload(student_code, batch_code, group),
                headers={"language": "zh_cn", "X-Requested-With": "XMLHttpRequest"},
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            if str(payload.get("code", "1")) not in {"1", "0"}:
                errors.append(f"{group}: {payload.get('msg', '接口返回失败')}")
                continue
            for row in _iter_dicts(payload):
                course = _course_from_row(row, group)
                if course is None:
                    continue
                key = (course["teachingClassId"], course["teachingClassType"])
                if key in seen:
                    continue
                seen.add(key)
                number = _pick(
                    row,
                    "number",
                    "courseNumber",
                    "courseCode",
                    "KCH",
                    "data-number",
                )
                if number is not None:
                    result.setdefault(str(number).strip(), []).append(course)
        except Exception as exc:
            errors.append(f"{group}: {exc}")

    if not result:
        detail = "；".join(errors[:3])
        raise RuntimeError(f"未能从当前选课页面读取课程目录{f'（{detail}）' if detail else ''}")

    normalized: dict[str, dict[str, str] | list[dict[str, str]]] = {}
    for number, courses in result.items():
        normalized[number] = courses[0] if len(courses) == 1 else courses
    return normalized


def save_catalog(catalog: dict[str, Any], path: str | Path) -> None:
    target = Path(path)
    target.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )
