# PUBG AFK Helper

[![Windows tests](https://github.com/chenbinghan666/pubg-afk-helper/actions/workflows/tests.yml/badge.svg)](https://github.com/chenbinghan666/pubg-afk-helper/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D6)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB)

基于 **OpenCV 屏幕识别、Windows 模拟输入与小地图变化检测**的 PUBG 自动流程工具。
识别大厅和结算界面，执行可配置的匹配、跳伞、移动、拾取与脱困流程，并通过置顶状态窗显示当前步骤。

*A Windows screen-recognition helper with configurable match flow, timed input,
minimap-based stuck detection and a click-through status overlay.*

## 功能

- **界面识别**：大厅、返回大厅、退出确认、人物结算和奖励页；连续识别确认并限制重复操作。
- **相对定位**：按屏幕尺寸缩放模板和坐标，支持对部分宽屏布局进行边缘对齐搜索。
- **对局流程**：大厅消失后计时跳伞、一次性右转、W＋左 Shift 持续前进、俯视后点按 F 拾取。
- **小地图防卡墙**：只比较右下角地图地形，屏蔽中央人物标记；先尝试 Shift＋C，再根据检测结果后退和左右横移。
- **置顶状态窗**：显示倒计时、动作、暂停原因和小地图检测指标；鼠标穿透，不抢游戏焦点。
- **可配置与可测试**：JSON 配置、模板录制工具、离线回归测试、Windows CI。

程序通过截图和普通操作系统输入工作，不读取游戏内存，不注入游戏进程。
项目仍处于早期阶段；固定计时和小地图变化都是近似判断，不能确认飞机、实际落地、拾取成功或奖励到账。
使用前请自行确认游戏规则和账号风险；本项目不提供反作弊绕过功能。

## 快速开始

需要 **Windows 10/11、Python 3.11+**，游戏使用主显示器的无边框窗口模式。

1. 下载 [最新 Release](https://github.com/chenbinghan666/pubg-afk-helper/releases/latest) 中的 `PUBG-helper.zip`，或克隆本仓库。
2. 安装 Python，勾选 **Add Python to PATH**。
3. 双击 `install.cmd`，等待依赖安装完成。
4. 首次使用先双击 **`preview.cmd`**，切回游戏检查识别日志；该模式不发送输入。
5. 确认识别正确后，关闭预览，双击 **`launch.cmd`** 启用自动操作。

```powershell
git clone https://github.com/chenbinghan666/pubg-afk-helper.git
cd pubg-afk-helper
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe bot.py             # 仅识别
.\.venv\Scripts\python.exe bot.py --live      # 启用输入
```

Git 克隆版本默认读取 `config.example.json`。自定义前复制为 `config.json`，本地配置不会提交到 Git：

```powershell
Copy-Item config.example.json config.json
```

仓库附带的是一套繁体中文界面的按钮裁剪模板。语言、游戏版本、HUD 比例或布局不同，需要重新录制模板，不能保证所有电脑直接适用。

## 默认流程

```text
识别大厅 → F 开始匹配
  → 连续 3 次检测到大厅消失 → 等待 120 秒
  → F 尝试跳伞 → 右转一次 → W + 左 Shift
  → 跳伞后 30 秒：俯视地面 → 每 0.5 秒点按 F
  → 小地图稳定约 1 秒：尝试跨越，必要时后退 / 横移
  → 死亡 / 结算：释放按键 → 返回大厅 → 下一轮
```

大厅消失也可能是加载画面，并不证明已经进入房间。所有时间均可调整。
右转默认位移 **4050**、俯视位移 **5000** 只是参考参数；实际角度取决于游戏灵敏度和鼠标设置。
疾跑和 Shift＋C 跨越需要与游戏键位及按住/切换设置一致。

## 操作键

| 按键 | 作用 |
| --- | --- |
| **F8** | 只暂停，释放脚本持有的按键 |
| **F7** | 只继续 |
| **F9** | 退出并释放按键 |
| **Ctrl+C** | 在终端停止程序 |

切出游戏时暂停输入，切回后自动继续；已开始的倒计时仍按真实经过时间计算。
鼠标角落暂停默认关闭，避免自动俯视触发保护，可用 `mouse_corner_pause` 单独启用。
进程被强制终止或电脑断电时无法执行按键清理。

## 配置与排错

完整参数、模板录制命令、小地图相对区域和灵敏度校准方法见 [配置与使用手册](docs/CONFIGURATION.md)。

| 问题 | 优先检查 |
| --- | --- |
| 没有识别或操作 | 置顶窗是否显示暂停、游戏是否在前台、窗口标题是否包含 `PUBG` |
| 开始或结算识别失败 | 界面语言、分辨率、HUD 比例与模板是否匹配 |
| 跳伞过早 / 过晚 | `movement.jump_delay_seconds` |
| 拾取过早 / 俯视方向不对 | `pickup_delay_after_jump_seconds`、`look_down_pixels` 和 Y 轴反转设置 |
| 右转角度不对 | 按实际转角校准 `turn_right_pixels` |
| 疾跑或跨越无效 | 键位、按住模式、运行权限以及游戏是否接受模拟输入 |
| 防卡墙误判 / 漏判 | 小地图区域、缩放、旋转设置和置顶窗的稳定比例指标 |

日志写入本地 `bot.log`。反馈前请移除账号、聊天、私人路径等信息。

## 开发

```powershell
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe package.py
```

测试模拟键鼠输入，不操作游戏。公开版本自动生成合成画面进行测试；本地如果存在
`reference_screens/`，可使用对应个人参考截图进行额外回归，该目录不纳入仓库或发行包。
CI 在 Windows 上使用 Python 3.11 和 3.12 运行测试。
离线测试通过不能替代不同硬件、游戏版本和灵敏度下的真实对局验证。

主要文件：`bot.py` 为状态机、识别与输入实现，`status_overlay.py` 为状态窗，
`prepare_templates.py` 为五界面模板生成工具，`package.py` 为发行包构建脚本。

欢迎通过 [Issues](https://github.com/chenbinghan666/pubg-afk-helper/issues) 反馈可复现问题，
提交修改前请阅读 [贡献说明](CONTRIBUTING.md)。版本记录见 [CHANGELOG](CHANGELOG.md)。

## 许可证

原创代码和文档使用 [MIT License](LICENSE)。游戏界面裁剪、名称与商标仍属于各自权利人，详见 [第三方声明](NOTICE.md)。本项目与 KRAFTON / PUBG 无隶属或官方合作关系。
