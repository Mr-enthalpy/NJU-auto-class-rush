from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from course_sync import refresh_catalog, save_catalog
from des import get_hash
from login import login
from select import watch


ROOT = Path(__file__).resolve().parent
USER_FILE = ROOT / "user.json"


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _course_list(course: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    return course if isinstance(course, list) else [course]


def _course_label(course: dict[str, Any]) -> str:
    detail = course.get("detail") or "无时间地点信息"
    location = course.get("location") or ""
    return f"{course.get('name', '未命名课程')} | {detail} {location}".strip()


def _print_help() -> None:
    print(
        "输入 add class_id1 class_id2 ... 添加课程号\n"
        "输入 del class_id1 class_id2 ... 删除课程号\n"
        "输入 detail class_id1 class_id2 ... 查看课程详情\n"
        "输入 load 加载上次保存的课程号\n"
        "输入 clear 清除当前课程号列表\n"
        "输入 show 查看当前课程号\n"
        "输入 exit 退出添加课程号环节\n"
        "输入 help 查看帮助。"
    )


def _merge_course(
    selected: dict[str, Any],
    class_id: str,
    course: dict[str, Any],
) -> None:
    if class_id not in selected:
        selected[class_id] = course
        return
    current_list = _course_list(selected[class_id])
    if all(item.get("teachingClassId") != course.get("teachingClassId") for item in current_list):
        current_list.append(course)
    selected[class_id] = current_list[0] if len(current_list) == 1 else current_list


def _select_teaching_classes(
    class_id: str,
    course: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    print(f"课程号 {class_id} 下有多个教学班，请输入要添加的序号（可输入多个）：")
    for index, item in enumerate(course, start=1):
        print(f"  {index}. {_course_label(item)}")
    chosen: list[dict[str, Any]] = []
    for raw_index in input("教学班序号: ").split():
        try:
            index = int(raw_index) - 1
        except ValueError:
            print(f"跳过无效序号：{raw_index}")
            continue
        if not 0 <= index < len(course):
            print(f"跳过无效序号：{raw_index}")
            continue
        if course[index] not in chosen:
            chosen.append(course[index])
    return chosen


def _load_saved_selection(
    saved: dict[str, Any],
    catalog: dict[str, dict[str, Any] | list[dict[str, Any]]],
) -> dict[str, Any]:
    selected: dict[str, Any] = {}
    for class_id, saved_course in saved.items():
        candidates = {
            item.get("teachingClassId"): item
            for item in _course_list(catalog.get(class_id, []))
        }
        for item in _course_list(saved_course):
            current = candidates.get(item.get("teachingClassId"))
            if current is not None:
                _merge_course(selected, class_id, current)
        if class_id not in selected:
            print(f"已跳过上一轮中不存在的课程：{class_id}")
    return selected


def _refresh_courses(
    session,
    student_code: str,
    batch_code: str,
    snapshot_path: Path,
) -> dict[str, dict[str, Any] | list[dict[str, Any]]]:
    try:
        catalog = refresh_catalog(session, student_code, batch_code)
        save_catalog(catalog, snapshot_path)
        print(f"✅ 已同步当前选课轮次课程：{len(catalog)} 个课程号")
        return catalog
    except Exception as exc:
        print(f"⚠️ 在线课程同步失败，将使用本地快照：{exc}")
        return _load_json(snapshot_path)


def _course_command_loop(
    catalog: dict[str, dict[str, Any] | list[dict[str, Any]]],
    saved_selection: dict[str, Any],
) -> dict[str, Any]:
    selected = _load_saved_selection(saved_selection, catalog)
    _print_help()
    while True:
        command = input(">>> ").strip()
        if command == "exit":
            return selected
        if command == "help":
            _print_help()
            continue
        if command == "show":
            if not selected:
                print("当前没有添加课程。")
            for class_id, course in selected.items():
                for item in _course_list(course):
                    print(f"课程号 {class_id}：{_course_label(item)}")
            continue
        if command == "clear":
            selected = {}
            print("已清除当前课程号列表")
            continue
        if command == "load":
            selected = _load_saved_selection(saved_selection, catalog)
            print("已加载本地保存且仍存在于当前轮次的课程")
            continue

        parts = command.split()
        if len(parts) < 2 or parts[0] not in {"add", "del", "detail"}:
            print("输入有误，请输入 help 查看帮助。")
            continue

        action = parts[0]
        for class_id in parts[1:]:
            if class_id not in catalog:
                print(f"课程号 {class_id} 不存在")
                continue
            candidates = _course_list(catalog[class_id])
            if action == "detail":
                print(f"课程号 {class_id}：")
                for key, value in candidates[0].items():
                    print(f"  {key}: {value}")
                for index, item in enumerate(candidates[1:], start=2):
                    print(f"  教学班 {index}: {_course_label(item)}")
                continue
            if action == "add":
                chosen = candidates if len(candidates) == 1 else _select_teaching_classes(class_id, candidates)
                for item in chosen:
                    _merge_course(selected, class_id, item)
                continue

            if class_id not in selected:
                print(f"当前列表中没有课程号 {class_id}")
                continue
            current = _course_list(selected[class_id])
            if len(current) == 1:
                del selected[class_id]
                print(f"已删除课程号 {class_id}")
                continue
            print(f"课程号 {class_id} 当前有多个教学班，请输入要删除的序号，或输入 all：")
            for index, item in enumerate(current, start=1):
                print(f"  {index}. {_course_label(item)}")
            raw_indexes = input("教学班序号: ").split()
            if "all" in raw_indexes:
                del selected[class_id]
                print(f"已删除课程号 {class_id} 的全部教学班")
                continue
            indexes = set()
            for raw_index in raw_indexes:
                try:
                    index = int(raw_index) - 1
                except ValueError:
                    continue
                if 0 <= index < len(current):
                    indexes.add(index)
            remaining = [item for index, item in enumerate(current) if index not in indexes]
            if not remaining:
                del selected[class_id]
            else:
                selected[class_id] = remaining[0] if len(remaining) == 1 else remaining
            print(f"已更新课程号 {class_id}")


def main() -> None:
    print("欢迎使用自动选课程序！")
    student_code = False
    loaded_user: dict[str, Any] = {}
    load_flag = False
    snapshot_path = ROOT / "courses.json"

    choice = input("是否加载上次保存的学号密码、课程和选课批次设置？(Y/N) ").strip().upper()
    if choice == "Y":
        try:
            loaded_user = _load_json(USER_FILE)
            student_code = bool(loaded_user.get("student_code", False))
            snapshot_path = ROOT / ("new_courses.json" if student_code else "courses.json")
            load_flag = True
            print("已加载上次保存的账号和选课设置")
        except Exception as exc:
            print(f"加载失败，将改为手动输入：{exc}")
    elif choice != "N":
        print("未识别到 Y/N，将改为手动输入。")

    if not load_flag:
        student_code = input("你是否是新生？(Y/N) ").strip().upper() == "Y"
        snapshot_path = ROOT / ("new_courses.json" if student_code else "courses.json")

    xh = str(loaded_user.get("XH", "")).strip()
    raw_password = str(loaded_user.get("RAW_PWD", "")).strip()
    if not xh:
        xh = input("学号: ").strip()
    if not raw_password:
        raw_password = input("密码: ").strip()

    config = _load_json(ROOT / "config.json")
    password = get_hash(raw_password, config["HASH_KEY"])
    session, batch_code = login(xh, password, config["AGENT"], student_code)
    catalog = _refresh_courses(session, xh, batch_code, snapshot_path)
    selected = _course_command_loop(catalog, loaded_user.get("CLASS_INFO", {}))

    save_data = {
        "XH": xh,
        "RAW_PWD": raw_password,
        "CLASS_INFO": copy.deepcopy(selected),
        "student_code": student_code,
    }
    USER_FILE.write_text(json.dumps(save_data, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")

    useful_info: list[dict[str, str]] = []
    class_name_list: list[str] = []
    for course in selected.values():
        for item in _course_list(course):
            useful_info.append(
                {
                    "teachingClassId": item["teachingClassId"],
                    "courseKind": item["courseKind"],
                    "teachingClassType": item["teachingClassType"],
                }
            )
            class_name_list.append(item.get("name", item["teachingClassId"]))

    if not useful_info:
        print("未添加课程，程序结束。")
        return

    def re_login():
        new_session, _ = login(xh, password, config["AGENT"], student_code)
        return new_session

    final_class_list = [
        {
            "operationType": "1",
            "studentCode": xh,
            "electiveBatchCode": batch_code,
            **course,
        }
        for course in useful_info
    ]
    watch(class_name_list, final_class_list, session, xh, re_login)


if __name__ == "__main__":
    main()
