---
name: commit-push
description: 更新 README、执行规范化 git 提交并推送到 origin 与 github 远程仓库。用于用户要求“提交并推送代码”“同步 README 的已实现功能并提交”“按 BliBIliRag 规范 commit/push”等场景。
---

# Commit Push

按以下固定流程执行。

## Context

先收集当前状态：

- 运行 `git status`
- 运行 `git diff HEAD`
- 运行 `git log --oneline -5`

## 任务

### Step 1: 更新 README.md

读取 `README.md` 和 `git diff HEAD`。若有新增功能，同步更新「已实现功能」章节（用 `✅` 标记）。无新功能则跳过。

### 注意事项

- 被 `.gitignore` 忽略的文件或目录，不做任何 `git add` / `git commit` 操作，直接跳过

### Step 2: Commit

按以下规范创建提交：

```text
<type>(BliBIliRag): <中文描述>
```

- `type`：`feat` / `fix` / `docs` / `refactor` / `test` / `chore` / `style` / `perf` / `ci` / `build` / `revert`
- `scope` 固定为 `BliBIliRag`
- 描述使用中文，简洁说明本次变更内容
- 提交信息中不要包含 `Co-Authored-By` 等署名信息

### Step 3: Push

依次推送到两个远程仓库：

```bash
git push origin main
git push github main
```
