# TASK-003.1-R61 启停脚本 PowerShell 路径与身份校验修复

## 根因

- stopper / launcher 通过子进程调用 `powershell` 读取 CIM 进程身份。在裁剪后的 PATH
  中 Windows PowerShell 5.1 不在 PATH，`subprocess` 抛 `FileNotFoundError`，身份信息读取
  失败而 fail-closed，表现为「无法读取进程身份信息（进程可能已退出）」，停止器无法回收
  工作台进程（R58 需人工核对 PID 后手动终止的原因）。
- 叠加问题：launcher 在进程刚启动时读取 CreationDate 可能为空，记录 `creation_date=null`；
  stopper 把启动时间缺失也当作不匹配拒绝。

## 修复

- 两脚本新增 `_powershell_exe()`：依次解析 `pwsh` → `powershell` →
  `%WINDIR%\System32\WindowsPowerShell\v1.0\powershell.exe` 全路径，避免依赖 PATH 中的
  裸命令名。
- 身份校验中 CreationDate 仅在记录侧与活动进程侧都有值时才比对；记录侧缺失（旧记录或
  启动瞬间未取到）不因此拒绝。PID 复用防护仍由每次启动随机生成、并与活动 health 探针
  比对的 `instance_id` 承担；可执行路径、命令行、PID、工作目录与命令行参数比对口径不变。
- launcher 读取 CreationDate 增加短暂重试。

## 真机闭环（本机 127.0.0.1:17890）

- 第一次：旧记录 `creation_date=null` 的实例（PID 864，子进程 27880）经修复后 stopper
  身份匹配并回收，端口关闭，运行记录清理。
- 第二次：重新由 launcher 启动（PID 25040），`creation_date` 正常写入；stopper 再次
  身份匹配回收，端口关闭，记录清理。
- 数据库 `workbench_rule / generation_history / comfy_task` 均为 0；Ollama、ComfyUI
  外部进程未触碰。

## 回归

- 后端：**224 passed, 1 warning**（`pytest-output.txt`，scripts 不进后端测试，全量兜底）。
- 前端：本切片无前端改动，沿用 R60 构建结果。

## 边界

- 未改动白名单、CSRF、回环绑定等安全口径；stopper 仍不按名称批量结束 Python。
- `WorkingDirectory` 经 Win32_Process 取不到（属性不存在），工作目录比对维持两侧都有值
  才比较的既有容错口径。
