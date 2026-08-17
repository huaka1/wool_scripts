# wool_scripts 自动同步 + 过滤

这个 fork 的目的：**上游模块随时更新，但 B 站等"在小火箭上不兼容"的站点规则被自动剥掉**。

## 分支结构

| 分支 | 内容 | 谁在更新 |
|------|------|----------|
| `builder`（默认） | 过滤脚本 + 配置 + 本工作流 | 手动 |
| `filtered` | 上游最新主干 + 过滤后的模块 | GitHub Actions 每3小时 |
| `mirror` | 上游主干纯净快照（参考用） | GitHub Actions 每3小时 |

## 小火箭导入地址

```
https://raw.githubusercontent.com/huaka1/wool_scripts/filtered/Surge/module/blockAds.module
```

小火箭 → 配置 → 模块 → 右上角 `+` → 粘贴上面链接。上游每 3 小时自动同步一次，不用再手动更新。

## 怎么加一个要过滤的网站

编辑 `filter/wool_filter_config.json`：

1. 在 `sites` 里加（京东已预置，可直接抄）：
   ```json
   "jd": {
     "domains": [".jd.com", ".360buy.com", ".jdpay.com", ".jdcloud.com"],
     "scripts": []
   }
   ```
2. 把名字加进 `enabled` 列表
3. 推送到 `builder` 分支 → 工作流自动重建 `filtered`

> 注意：`domains` 填站点域名，脚本会按"整词匹配"剥掉所有相关规则行；`scripts` 填 [Script] 段里要按脚本名剥掉的名字（B 站那种 `bilibili.airborne` 等）。

## 手动同步

GitHub → Actions → Sync & Filter → Run workflow（黄色按钮）。

## 常见问题

- **上游改动了但 filtered 没变**：看 Actions 最近一次运行日志；`No changes vs upstream` 说明上游该文件没动。
- **想关掉某个站的过滤**：从 `enabled` 里删掉名字，推 builder。
