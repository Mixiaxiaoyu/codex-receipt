# CODEX RECEIPT 使用说明

CODEX RECEIPT 是一个本地 Codex skill，用来读取允许访问的本机 Codex 历史记录，统计你的使用行为，生成一张可以分享的“Codex 小票”。

它不是官方账单，也不是 OpenAI 的计费记录。它生成的是一份本地个人总结：包含使用统计、工作节奏、能力倾向、Codex Working Persona，以及一张带像素风人格插图的长图小票。

## 这个 skill 是干什么的

CODEX RECEIPT 会把本地 Codex 使用痕迹整理成一个视觉化纪念票据：

- 扫描本机 Codex 历史数据。
- 聚合会话数、turn 数、工具调用、命令运行、文件修改、活跃天数等统计。
- 在日志有精确 token 字段时汇总精确 token。
- 在日志缺少精确 token 或只提供累计字段时，标注为估算或覆盖率不足。
- 根据使用行为生成非医学、非人格诊断性质的 Codex Working Persona。
- 为本次结果生成一张 AI 像素人格插图。
- 使用固定的 receipt texture skin 渲染最终小票，而不是用 AI 直接生成整张小票。
- 输出公开版和私有版报告，公开版会避免暴露原始 prompt、路径、邮箱、API key 等敏感信息。

## 它能生成什么

一次正常运行会生成一个输出目录，常见文件包括：

```text
output/
  receipt-share-final.png
  receipt-share.png
  receipt-full-01.png
  receipt.html
  receipt-full.html
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

最主要给用户看的文件是：

- `receipt-share-final.png`：最终分享图。
- `report-public.html`：公开安全报告。
- `report-private.html`：本地私有报告。
- `coverage-report.json`：数据覆盖情况。
- `visual-check-report.json`：视觉渲染和素材使用检查。

## 语言模式

默认输出英文版。

如果需要中文版，可以使用 `cn` 或 `@cn`：

```powershell
python -m codex_receipt cn --period all --out output-cn
```

PowerShell 里如果使用 `@cn`，需要加引号：

```powershell
python -m codex_receipt '@cn' --period all --out output-cn
```

也可以显式传语言参数：

```powershell
python -m codex_receipt generate --period all --out output-cn --language zh-cn
```

## 推荐用法

完整真实运行建议分两步：先准备数据和插图 prompt，再生成插图并渲染。

第一步，准备数据：

```powershell
python -m codex_receipt prepare --period all --out output
```

这一步会生成：

```text
output/receipt-data.json
output/persona-illustration-prompt.txt
```

第二步，用 `persona-illustration-prompt.txt` 生成本次专属的 AI 像素插图，并保存为：

```text
output/persona-illustration-raw.png
```

第三步，渲染最终小票：

```powershell
python -m codex_receipt render --out output --persona-illustration output/persona-illustration-raw.png
```

生成完成后，查看：

```text
output/receipt-share-final.png
```

## 一步生成

如果已经有一张可用的人格插图，可以直接运行：

```powershell
python -m codex_receipt generate --period all --out output --persona-illustration output/persona-illustration-raw.png
```

中文版：

```powershell
python -m codex_receipt cn --period all --out output-cn --persona-illustration output-cn/persona-illustration-raw.png
```

## Demo 模式

Demo 模式使用固定演示数据，适合检查视觉效果，不代表真实使用量：

```powershell
python -m codex_receipt demo --out output-demo
```

如果要看真实效果，不要用旧的 demo 输出目录，建议换一个新的 `--out` 目录，或先重新运行 `prepare` 和 `render`。

## Token 数据为什么可能不等于官方账单

CODEX RECEIPT 读取的是本机可见的 Codex 日志，不是 OpenAI 官方计费系统。

因此 token 有几种情况：

- 如果 session 里有精确 turn-level token 字段，小票会使用精确值。
- 如果只有累计 token 字段，小票会按可见累计增量处理，并标注覆盖情况。
- 如果缺少精确 token 字段，只能根据可见活动量估算，并在小票中显示 `TOKEN EST.`。
- 如果本地日志没有保存某些会话、被清理、被归档到不可访问位置，统计会低于真实使用感受。

所以这个 skill 可以尽量准确地反映本机可见数据，但不能保证等同于官方用量或账单。

## 视觉规则

最终小票不是 AI 生成整张图，而是代码渲染：

- 小票背景使用 `assets/receipt-skin-top.png`、`assets/receipt-skin-mid.png`、`assets/receipt-skin-bottom.png`。
- `OUTPUT TIME` 印章使用 `assets/stamp-output-time.png`，再叠加动态生成时间。
- 人格插图由 AI 生成单独素材，再做像素化处理后放入固定插图区域。
- 原始参考图不会被打包进最终输出。
- 最终 HTML 会由 headless browser 截图；如果当前机器浏览器截图失败，会使用 PowerShell GDI fallback 渲染，并在 `visual-check-report.json` 里记录。

## 常用命令

```powershell
python -m codex_receipt prepare --period all --out output
python -m codex_receipt render --out output --persona-illustration output/persona-illustration-raw.png
python -m codex_receipt generate --period all --out output --persona-illustration output/persona-illustration-raw.png
python -m codex_receipt cn --period all --out output-cn --persona-illustration output-cn/persona-illustration-raw.png
python -m codex_receipt '@cn' --period all --out output-cn --persona-illustration output-cn/persona-illustration-raw.png
python -m codex_receipt demo --out output-demo
python -m codex_receipt inspect-coverage
python -m codex_receipt clear-cache --out output
python -m codex_receipt reset-identity --out output
python -m codex_receipt benchmark --out output-benchmark
```

## 什么时候用它

适合用在这些场景：

- 想生成一张 Codex 使用纪念小票。
- 想看自己和 Codex 协作的行为统计。
- 想知道本机历史数据覆盖率如何。
- 想生成一个可以分享但不暴露敏感原文的总结图。
- 想生成英文默认版，或用 `@cn` 生成中文版。

不适合用在这些场景：

- 查询官方账单。
- 作为财务、审计或报销凭证。
- 精确还原所有 OpenAI 后端 token 消耗。
- 公开分享包含原始 prompt、私有路径或密钥的内部日志。

## 验证输出

生成后建议查看：

```text
output/visual-check-report.json
output/coverage-report.json
output/privacy-report.json
```

重点确认：

- `language` 是否符合预期。
- `stamp_texture_present` 是否为 `true`。
- `ai_illustration_supplied` 是否为 `true`。
- `receipt_share_final_exists` 是否为 `true`。
- `raw_prompts_in_public_output` 是否为 `false`。
- token 显示是 `TOKEN` 还是 `TOKEN EST.`。

## 开发检查

修改代码后可以运行：

```powershell
python -m unittest discover -s tests
python -m compileall codex_receipt tests
```

如果修改视觉渲染，建议重新生成英文版和中文版各一份，检查 `receipt-share-final.png` 与 `visual-check-report.json`。
