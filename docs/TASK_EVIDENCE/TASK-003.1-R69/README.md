# TASK-003.1-R69 规则库前端删除入口（两步态确认）

## 验收范围

- 后端 `DELETE /api/rules`（R80，含 level 校验与会话 CSRF 保护）早已就绪并由
  `test_rule_api.py::test_upsert_and_delete_rule_via_api` 覆盖；前端规则清单此前只读展示，
  漏接删除入口。本切片补齐前端闭环，后端无改动。
- 基线：health `0.1.0-dev.5`；走查前 `rules=0`、`history=0`、`tasks=0`、`profiles=13`、
  `workflows=22`、`model_identities=16`。

## 实现要点（前端）

- `App.tsx`：引入既有 `apiDelete`；新增 `deletingRule` 确认态状态与 `removeRule(rule)`。
  - 两步确认：首次点击「删除」只进入确认态（按钮变「确认删除？」危险色），不直接删除；
    再次点击才调 `DELETE /api/rules`，请求体 `{level, scope_key, rule_key}`，与后端 `RuleDelete` 契约一致。
  - 删除成功后重新拉取 `/api/rules` 刷新清单，回显「规则已删除。」；失败回显「规则删除失败：…」。
  - 不使用原生 `window.confirm`（同步阻塞主线程，已验证会卡死 CDP 管道）。
- 规则库标题由「规则库（只读）」改为「规则库」；说明更新为：记录来自档案导入，可删除纠错，
  前端不提供手动新增或修改，新增与覆盖仍走档案导入。
- `styles.css`：规则行 meta 内按钮紧凑尺寸；确认态 `.danger` 沿用既有暖橙警示色板
  （`#d18b68` / `#5a3325` / `#e8c3ae`），不引入新色。

## 真机闭环（本机 127.0.0.1:17890，PID 18340 → 重启 21912）

- 种子：bootstrap 换 CSRF 后 `POST /api/rules` 写入一条临时规则
  （checkpoint / pony.safetensors / steps=32 / author / authoritative），`GET /api/rules` 计数 1。
- 浏览器：服务与设置页规则库出现该规则行，meta 区「作者 / 权威 / v1 / 删除」；
  点「删除」进入确认态，按钮变「确认删除？」暖橙，规则行仍在；再点确认，调用删除接口，
  清单刷新为「规则库为空。」，消息「规则已删除。」。
- 直连复核：`rules=0`，diagnostics 计数 rules 0 / history 0 / tasks 0 / identities 16 /
  workflows 22 / profiles 13，回到基线；console 无报错。
- 截图：`r69-rule-row.png`（规则行与删除按钮）、`r69-confirm.png`（确认删除态）、
  `r69-after-delete.png`（删除后空库与成功消息）、`r69-empty-copy.png`（新文案空库复核）。

## 收尾

- 临时规则已删除，规则库回到空基线；未改动规则文件、未新增持久样本。
- stopper 按结构化身份回收实例（18340、21912，含子进程），端口 17890 关闭；Ollama、ComfyUI 未触碰。

## 回归

- 后端：**231 passed, 1 warning**（`pytest-output.txt`；后端无改动，全量回归兜底；
  StarletteDeprecationWarning 为遗留，与本项目无关）。
- 前端：`tsc -b && vite build` 绿（`frontend-build.txt`）；产物
  `index-Di176E0j.js` 182.20 kB / gzip 58.10 kB，`index-YZUDVJS8.css` 9.58 kB / gzip 2.36 kB。

## 边界与遗留

- 前端仍不提供规则手动新增/编辑表单；规则写入与覆盖继续走档案导入（`/api/profiles/import`）
  或后端既有 upsert 接口。
- 删除为单条按 level/scope_key/rule_key 定位；批量删除、删除前二次预览、规则历史版本回退仍留后续。
- 未改动白名单写入、CSRF、回环绑定、unknown 不臆测等安全口径。
