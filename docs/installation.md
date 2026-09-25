[Reading 131 lines from start (total: 131 lines, 0 remaining)]

# 安装与真实游戏测试

[English](installation.en.md)

这份说明讲的是**当前开发测试版怎么安装**。

现在还不是普通玩家正式版。TS4Script 还没有完成真实游戏验证，所以这里只用于受控测试。

## 开始前需要什么

你需要：

- 《The Sims 4》；
- 在游戏设置里开启“自定义内容与 Mod”和“允许脚本 Mod”；
- Python 3.9 或更高版本，用来运行电脑上的本地程序；
- 只有需要自己重新构建 TS4Script 时，才需要 CPython 3.7。

当前测试目标：

```text
The Sims 4 1.127.41.1030
```

其他游戏版本目前没有验证。

## 1. 启动电脑上的本地程序

在仓库根目录运行：

```powershell
py -m pip install -e .
sims-companion-bridge
```

然后打开：

```text
http://127.0.0.1:8765
```

能看到游戏窗口页面即可。

## 2. 准备 TS4Script 测试包

如果你自己从源码构建：

```powershell
python game-mod/build_ts4script.py
py scripts/preflight.py
```

最后必须看到：

```text
GATE=READY_FOR_GAME_TEST
```

才继续。

生成的文件是：

```text
game-mod/dist/SimsCompanionBridge.ts4script
```

## 3. 放进 Mods

先把《The Sims 4》完全关闭。

只把 `.ts4script` 放进 Mods 里的一个浅层文件夹，例如：

```text
Mods/
  SimsCompanionBridge/
    SimsCompanionBridge.ts4script
```

不要把整个源码仓库、测试文件、数据库或构建记录一起复制进去。

不同电脑的 Sims 4 用户文件夹位置可能不同，尤其是 Windows 文档目录被 OneDrive 等工具改过时。以游戏实际使用的 Mods 文件夹为准，不要死认一个固定路径。

## 4. 启动游戏

正常启动《The Sims 4》。

确认：

- 自定义内容与 Mod：开启；
- 允许脚本 Mod：开启。

修改脚本 Mod 设置或替换 TS4Script 后，需要完全退出并重新启动游戏。

## 5. 当前测试只做两件事

先输入：

```text
scb.status
```

再输入：

```text
scb.snapshot
```

这轮只检查：

1. 游戏有没有加载脚本；
2. 能不能读到当前存档、地点和 Sim 状态；
3. 能不能把一次只读状态发给本地程序；
4. 游戏窗口能不能显示真实游戏世界。

开发者完整检查项见：[真实游戏测试清单](GAME_TEST_CHECKLIST.md)。

## 这次测试不会做什么

不会：

- 控制 Sim；
- 修改自治；
- 改钱、关系、技能、职业、CAS 或存档；
- 执行 AI 动作；
- 开启主动消息；
- 连接远程 AI 服务。

## 普通玩家现在要不要装？

目前不建议。

正式面向普通玩家的版本，不应该要求玩家安装 Python 3.7、自己编译脚本、运行 Preflight 或理解源码仓库。

在真实游戏验证完成前，请把这里当成开发测试说明，而不是正式安装教程。

[executed on device: WIN-15QI2I7SNM4 (3b0744ec-1adf-45d0-b2db-5f62af795dec)]