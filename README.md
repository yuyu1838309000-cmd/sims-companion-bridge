[Reading 135 lines from start (total: 135 lines, 0 remaining)]

# Sims Companion Bridge

[English](README.en.md)

Sims Companion Bridge 用来把一个**已经存在的 AI 伴侣或聊天服务**接到《The Sims 4》。

目标很简单：让 AI 知道游戏里正在发生什么，并在一个独立的游戏聊天窗口里和你交流，不把游戏聊天和日常聊天混在一起。

**目前版本只读取游戏状态，不控制 Sim。**

> 当前状态：本地演示已经可以运行，也能生成 TS4Script 测试包。
> 但这个 TS4Script **还没有完成真实游戏测试**，所以现在还不是普通玩家下载后直接玩的正式版本。

## 适合谁？

### 普通《模拟人生4》玩家

这个项目最终是给“不写代码也想让自己的 AI 伴侣进入 Sims 世界”的玩家使用的。

但目前还是开发测试阶段。
如果你只想下载一个 Mod、放进 Mods 文件夹就开始玩，建议等通过真实游戏测试后的版本。

### 已经有自己的 AI 服务的人

如果你已经有自己的 AI 伴侣、聊天后端或 Agent，这个项目的目标是**直接连接它**，而不是在 Mod 里再造一个新的 AI 人格。

目前连接自定义 AI 仍需要开发者接入，还没有“填 API Key 就能用”的简单设置页面。

### 开发者

现在已经可以：

- 运行不需要游戏的本地演示；
- 查看游戏状态协议；
- 构建只读 TS4Script；
- 编写自己的 AI 后端连接代码。

精确支持情况见：[兼容与适用范围](docs/compatibility.md)。

## 现在能做什么？

| 功能 | 当前状态 |
| --- | --- |
| 本地游戏窗口演示 | 可以 |
| 本地保存世界状态和事件 | 可以 |
| 使用 Mock AI 聊天 | 可以 |
| 只读游戏状态协议 | 自动测试通过 |
| 构建 Python 3.7 TS4Script | 可以 |
| 在真实《The Sims 4》中加载验证 | 还没有完成 |
| AI 控制 Sim | 没有开放 |
| 普通玩家一键安装 | 还没有 |

## 它是怎么工作的？

```text
The Sims 4
   |
   | 读取游戏状态
   v
电脑上的本地程序
   |
   +--> 保存游戏世界和事件
   |
   +--> 把需要的游戏信息交给 AI
   |
   v
独立游戏聊天窗口
```

游戏里的脚本尽量保持很小。AI 模型、记忆、数据库和复杂网络逻辑都放在游戏外面。

## 不装游戏也可以先看演示

本地演示不需要《The Sims 4》，也不需要 API Key。

需要 Python 3.9 或更高版本：

```powershell
py -m pip install -e .
sims-companion-bridge
```

然后打开：

```text
http://127.0.0.1:8765
```

停止时按 `Ctrl+C`。

## 现在怎么装进《The Sims 4》？

目前只建议用于**开发测试**，还不是普通玩家安装流程。

如果你要参加测试，请先看：[安装与游戏测试](docs/installation.md)。

不要直接把开发目录整份复制进 Mods。

## 怎么接自己的 AI？

当前演示默认使用本地 Mock AI，不需要联网。

开发者可以通过 Python 接口接自己的 AI 服务，技术说明见：[后端连接协议](docs/backend-protocol.md)。

面向普通用户的 AI 服务设置页面还没有完成。

## 当前安全限制

目前游戏端：

- 不控制 Sim；
- 不修改钱、关系、技能、职业或存档；
- 不执行 shell 命令，也不随意读写电脑文件；
- 游戏状态只发送到本机地址；
- 外部 AI 返回的内容不会被直接当成游戏命令执行。

更多说明见：[安全说明](SECURITY.md)。

## 文档

普通用户先看：

- [安装与游戏测试](docs/installation.md)
- [兼容与适用范围](docs/compatibility.md)

开发者再看：

- [架构](docs/architecture.md)
- [AI 后端连接协议](docs/backend-protocol.md)
- [开发流程](docs/development-workflow.md)
- [真实游戏测试清单](docs/GAME_TEST_CHECKLIST.md)

## 开源协议

MIT，见 [LICENSE](LICENSE)。

[executed on device: WIN-15QI2I7SNM4 (3b0744ec-1adf-45d0-b2db-5f62af795dec)]