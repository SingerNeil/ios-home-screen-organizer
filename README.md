# 理屏（Liping）

一个完全在本机运行的 macOS iPhone 主屏幕分析与整理工具。通过公开的
SpringBoardServices 协议读取已配对设备的图标布局，提供诊断、滑动成本、布局观察、
告别文和四种整理预览。

本项目是独立净室实现，不包含、复制或修改任何被研究应用的可执行文件、资源、授权逻辑
或服务端代码。

## 当前能力

- USB 设备发现与配对会话重试；
- 读取 iPhone/iPad 主屏幕页面、文件夹及应用信息；
- 本地布局评分、分类统计和滑动成本估算；
- 本地生成“屏幕镜像”和“告别旧布局”文案；
- 专注、放松、极简、美观四种布局预览；
- 写入前重新扫描、设备匹配、源布局哈希校验与应用集合校验；
- Apply 前自动备份，Restore 前再次创建安全备份；
- 不需要登录、订阅、许可证服务器、云端 AI 或 API Key。

## 已验证范围

- macOS 14+ / Apple Silicon；
- Python 3.12；
- iPhone 17 Pro / iOS 27.0 的真实 USB 连接与只读流程；
- 187 个应用、6 页布局的扫描、诊断、文案生成和 6→4 页预览；
- plist 中 `datetime`、二进制数据及 UID 的无损 JSON 往返；
- 原生 SwiftUI GUI、包内后端和 ad-hoc 签名。

真实设备的 Apply/Restore 写入仍应谨慎测试。本项目默认把预览与写入分开，绝不在扫描时
自动修改手机。

## 构建

依赖：

- macOS 14 或更高版本；
- Apple Command Line Tools；
- Python 3.12；
- 已解锁并信任当前 Mac 的 iPhone/iPad（仅真机功能需要）。

```bash
make test
make build
make verify
```

默认产物位于 `build/理屏.app`。如需复制到其他位置：

```bash
make install INSTALL_APP="/absolute/path/理屏.app"
```

构建使用本地 ad-hoc 签名，不包含 Developer ID 签名或 Apple 公证。

## 目录结构

```text
Sources/UnjiggleRebuilt/   SwiftUI 前端
backend/unjiggle_rebuilt/  设备桥接、分析、预览、备份与恢复
tests/                     后端单元测试
scripts/                   依赖安装、构建、验证与本地安装
config/                    macOS App 元数据
docs/                      净室逆向边界记录
```

## 安全约束

布局写入必须同时满足：

1. 设备 UDID 与预览时一致；
2. 当前布局哈希与预览源布局一致；
3. 预览前后应用集合完全相同；
4. 创建可恢复备份；
5. 用户明确确认 Apply。

任何一项不满足都会拒绝写入。

## 后续开发建议

- 为真实 Apply/Restore 增加专门的真机回归测试设备；
- 增加布局可视化拖放编辑器；
- 使用 App Store 分类元数据替代当前的本地关键词分类；
- 增加备份浏览与恢复界面；
- 配置 Developer ID、Hardened Runtime 和公证发布流程；
- 拆分 GPL 设备桥接进程，进一步明确分发许可边界。

## 许可证

仓库自有代码采用 MIT License。设备通信依赖
[`pymobiledevice3`](https://github.com/doronz88/pymobiledevice3) 9.10.1，采用
GPL-3.0-or-later。分发包含该依赖的应用包时，必须同时遵守其许可证要求。详见
[NOTICE.md](NOTICE.md)。
