# NJU-auto-class-rush

适用于南京大学选课系统的半自动选课脚本，支持自动登录、实时同步当前选课轮次的课程目录，以及课程状态监视。

## 使用

1. 安装依赖：

   ```bash
   pip install -r requirements.txt
   ```

2. 在项目目录运行：

   ```bash
   python main.py
   ```

程序会先登录南京大学选课系统，再从当前页面对应的选课轮次同步课程号、教学班号、课程类别和时间地点。同步失败时才使用项目内的 `courses.json` 或 `new_courses.json` 快照，因此不需要每学期手工替换旧教学班号。

验证码识别使用当前站点仍在使用的四点验证码图片格式；如识别失败，程序会自动重新获取验证码并重试。

## HTML 快照转换

如果手里有课程页 HTML 快照，可将其放入 `course/` 目录，再运行：

```bash
python course/temp.py --output new_courses.json
```

课程页当前仍使用 `tr.course-tr`、`data-number` 和 `data-teachingclassid` 字段，转换脚本同时兼容常见的新字段写法。

## 注意

脚本只会在你明确选择课程并退出课程配置环节后开始持续请求选课接口。请遵守学校选课系统的使用规定，并合理设置 `config.json` 中的 `WAIT_TIME`。
