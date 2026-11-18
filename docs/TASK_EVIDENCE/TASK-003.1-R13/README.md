# TASK-003.1-R13 证据目录

M3 第八切片：旧档案扫描清单与候选预览只读接口。

## 交付物

- `backend/profile_source.py`：profiles 目录扫描、清单汇总、单档案候选预览；目录可由 `WORKBENCH_PROFILES_DIR` 覆盖；损坏/不可读容错。
- `backend/main.py`：`GET /api/profiles`、`GET /api/profiles/{file_name}`（404）。
- `backend/test_profile_source.py`：清单汇总、候选预览不落库、404、目录缺失容错 4 例。
- `backend/profile_parser.py`：IDENTITY 节不再产生规则候选。

## 切片边界

- 只读预览：接口不写 `workbench_rule` 表；候选审核导入落库留后续切片。
- 档案目录默认为仓库 `legacy-materials/profiles`；测试指向临时目录。

## 验收记录

| 项 | 结果 |
| --- | --- |
| 后端 pytest | 109 passed, 1 warning（见 `pytest-output.txt`） |
| 前端构建 | tsc -b && vite build exit 0（见 `frontend-build.txt`） |
| 真机闭环 | `samples/smoke-profiles.json`（13 份清单 / 预览 11 候选 / 404 / 入库 0） |
