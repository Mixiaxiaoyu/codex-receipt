# CODEX RECEIPT

CODEX RECEIPT 是一个本地 Codex skill，用来读取你本机可访问的 Codex 历史记录，生成一张可分享的“Codex 使用小票”。

它会统计你的会话、turn、工具调用、命令运行、文件修改、token 覆盖情况等信息，生成一个非诊断性质的 Codex Working Persona，并为本次结果生成一张 AI 像素人格插图，最后渲染成一张长图小票。

它不是官方账单，也不是 OpenAI 计费记录。它只基于本机可见日志做个人总结。

## 最快用法

在 Codex 里直接调用这个 skill 即可，例如：

```text
用 codex-receipt 生成我的小票
```

或：

```text
跑一下 Codex Receipt
```

默认行为：

- 直接开始完整生成流程，不先问问题。
- 默认扫描全部可见历史记录。
- 默认输出英文版。
- 自动生成本次专属 AI 像素人格插图。
- 自动渲染最终小票。
- 生成完成后返回最终文件路径和必要提醒。

如果要中文版，在请求里加 `@cn`：

```text
@cn 生成我的 Codex 小票
```

## 它会生成什么

主要结果在输出目录里，默认是 `output/`。

最重要的文件：

```text
output/receipt-share-final.png
```

这是最终分享图。

其他常见文件：

```text
output/
  receipt-share-final.png
  receipt-share.png
  receipt.html
  persona-illustration-raw.png
  persona-illustration-processed.png
  persona-illustration-prompt.txt
  receipt-data.json
  statistics.json
  persona.json
  coverage-report.json
  privacy-report.json
  performance-report.json
  visual-check-report.json
  report-public.html
  report-private.html
  manifest.json
```

建议重点看：

- `receipt-share-final.png`：最终小票图。
- `report-public.html`：适合查看和分享摘要的公开安全报告。
- `report-private.html`：本地私有报告。
- `coverage-report.json`：本地日志覆盖情况。
- `visual-check-report.json`：视觉渲染、素材、插图、印章检查。

## 英文和中文

英文是默认版本，不需要额外参数。

中文有三种方式：

```text
@cn 生成我的 Codex 小票
```

```powershell
python -m codex_receipt cn --period all --out output-cn
```

```powershell
python -m codex_receipt generate --period all --out output-cn --language zh-cn
```

PowerShell 里如果使用 `@cn` 命令，需要加引号：

```powershell
python -m codex_receipt '@cn' --period all --out output-cn
```

## 它能做什么

CODEX RECEIPT 可以：

- 扫描本机 Codex 历史记录。
- 统计使用天数、会话数、turn 数、工具调用、命令运行和文件修改。
- 汇总可见 token 数据，并标明是否精确。
- 根据使用行为生成 Codex Working Persona。
- 生成本次专属 AI 像素人格插图。
- 使用固定小票皮肤渲染最终长图。
- 输出公开安全报告和本地私有报告。
- 支持英文默认版和 `@cn` 中文版。

它不会：

- 查询官方账单。
- 作为报销、审计或财务凭证。
- 保证等同于 OpenAI 后端真实 token 消耗。
- 把原始 prompt、私有路径、邮箱、API key 放进公开输出。
- 用 AI 直接生成整张小票。

## Token 为什么可能显示为估算

CODEX RECEIPT 只能读取本机可见 Codex 日志。

因此 token 有三种情况：

- 如果日志里有精确 turn-level token 字段，小票会显示精确值。
- 如果日志里只有累计 token 字段，小票会按可见增量处理，并显示覆盖情况。
- 如果日志缺少精确 token 字段，小票会显示 `TOKEN EST.`，表示这是估算。

所以小票中的 token 更像“本机可见记录总结”，不是官方账单数字。你的实际使用感受可能比小票更大，常见原因是本地日志不完整、旧 session 被清理、某些 session 没有精确 token 字段，或只能看到累计字段。

## 视觉规则

最终小票是代码渲染，不是 AI 生成整张图。

视觉结构：

- 小票背景来自 `assets/receipt-skin-top.png`、`assets/receipt-skin-mid.png`、`assets/receipt-skin-bottom.png`。
- `OUTPUT TIME` 印章使用 `assets/stamp-output-time.png`，再叠加动态生成时间。
- AI 只负责生成人格插图，不负责生成整张小票。
- 人格插图会被像素化处理后放入固定区域。
- 原始参考图不会被打包进最终输出。

如果 headless browser 截图失败，程序会使用 PowerShell GDI fallback 渲染，并在 `visual-check-report.json` 里记录。

## 命令行用法

在 Codex 聊天里调用 skill 时，通常不需要手动跑这些命令。下面命令适合开发、调试或高级用户。

准备数据和插图 prompt：

```powershell
python -m codex_receipt prepare --period all --out output
```

这会生成：

```text
output/receipt-data.json
output/persona-illustration-prompt.txt
```

然后用 `persona-illustration-prompt.txt` 生成 AI 插图，并保存为：

```text
output/persona-illustration-raw.png
```

最后渲染小票：

```powershell
python -m codex_receipt render --out output --persona-illustration output/persona-illustration-raw.png
```

如果已经有插图素材，可以一步渲染：

```powershell
python -m codex_receipt generate --period all --out output --persona-illustration output/persona-illustration-raw.png
```

中文版：

```powershell
python -m codex_receipt cn --period all --out output-cn --persona-illustration output-cn/persona-illustration-raw.png
```

Demo 模式使用固定演示数据，只适合看视觉效果：

```powershell
python -m codex_receipt demo --out output-demo
```

注意：命令行本身不会自动调用图片生成工具。完整 AI 插图版建议在 Codex 聊天里调用 skill，由 agent 按流程生成插图并渲染。

## 常用检查

生成后建议检查：

```text
output/visual-check-report.json
output/coverage-report.json
output/privacy-report.json
```

重点字段：

- `language`：输出语言。
- `stamp_texture_present`：是否找到印章素材。
- `ai_illustration_supplied`：是否使用了本次 AI 插图。
- `receipt_share_final_exists`：最终分享图是否生成。
- `raw_prompts_in_public_output`：公开输出是否避免原始 prompt。
- `token_display_label`：token 是精确值还是估算。

## 目录结构

运行 skill 需要保留：

```text
SKILL.md
README.MD
agents/
assets/
codex_receipt/
references/
```

其中：

- `SKILL.md`：给 Codex agent 看的执行说明。
- `README.MD`：给用户看的使用说明。
- `agents/`：Codex UI 展示信息。
- `assets/`：小票皮肤、印章等视觉素材。
- `codex_receipt/`：核心 Python 代码和渲染逻辑。
- `references/`：产品规格、视觉规范、验收清单。

`.git/` 是仓库元数据，不影响 skill 运行，但建议保留。
