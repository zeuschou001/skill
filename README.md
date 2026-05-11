# Skill Collection

## 中文介绍

这个仓库用于收集可复用的 Codex 技能目录。每个子目录都是一个独立 skill，包含 `SKILL.md` 入口文件、可选的 `agents/` 配置、参考资料和示例资产。

### 当前目录

| 目录 | 说明 |
| --- | --- |
| `dify-chatflow-dsl-builder/` | 用于构建和修复本地 Dify Chatflow 应用，重点覆盖节点连线、RAG 绑定、多轮路由、DSL 导入导出和草稿 JSON 回读校验。 |
| `outline-analysis/` | 用于把业务材料、原型、文档、表格、截图等输入转换为可评审的需求分析和概要设计输出，强调来源可追溯和结构化交付。 |

### 使用方式

将需要的 skill 目录安装或复制到 Codex 可读取的 skills 路径中，然后在任务中按 skill 名称调用。例如：

```text
Use $dify-chatflow-dsl-builder to repair the local Dify Chatflow.
Use $outline-analysis to analyze these requirement materials.
```

每个 skill 的具体流程、约束和参考资料以对应目录下的 `SKILL.md` 为准。

## English Introduction

This repository collects reusable Codex skill directories. Each subdirectory is an independent skill with a `SKILL.md` entry point, optional `agents/` configuration, references, and example assets.

### Included Skills

| Directory | Description |
| --- | --- |
| `dify-chatflow-dsl-builder/` | Builds and repairs local Dify Chatflow apps, with emphasis on node wiring, RAG bindings, multi-turn routing, DSL import/export, and draft JSON readback verification. |
| `outline-analysis/` | Turns business materials, prototypes, documents, spreadsheets, screenshots, and related inputs into reviewable requirement analysis and high-level design deliverables with source traceability. |

### Usage

Install or copy the needed skill directory into a Codex-readable skills path, then invoke it by skill name in a task. For example:

```text
Use $dify-chatflow-dsl-builder to repair the local Dify Chatflow.
Use $outline-analysis to analyze these requirement materials.
```

Refer to each skill's `SKILL.md` for its workflow, constraints, and bundled references.

## License

This repository is licensed under the Apache License 2.0. See [LICENSE](./LICENSE) for details.
