# immortalwrt24.10-6.6-cmcc_rax3000m

[![Build OpenWrt](https://github.com/XiaoXinCodes/immortalwrt24.10-6.6-cmcc_rax3000m-237/actions/workflows/openwrt-builder.yml/badge.svg)](https://github.com/XiaoXinCodes/immortalwrt24.10-6.6-cmcc_rax3000m-237/actions/workflows/openwrt-builder.yml)
[![GitHub release](https://img.shields.io/github/v/release/XiaoXinCodes/immortalwrt24.10-6.6-cmcc_rax3000m-237?include_prereleases&label=%E5%9B%BA%E4%BB%B6%E7%89%88%E6%9C%AC)](https://github.com/XiaoXinCodes/immortalwrt24.10-6.6-cmcc_rax3000m-237/releases)
[![License](https://img.shields.io/github/license/XiaoXinCodes/immortalwrt24.10-6.6-cmcc_rax3000m-237?label=%E5%8D%8F%E8%AE%AE)](LICENSE)

为 **中国移动定制版 RAX3000M**（CMCC RAX3000M）打造的 ImmortalWrt 固件，基于 `openwrt-24.10` + `6.6` 内核，大功率无线预调，开箱即用。

## 固件信息

| 项目 | 说明 |
| --- | --- |
| 源码 | [padavanonly/immortalwrt-mt798x-6.6](https://github.com/padavanonly/immortalwrt-mt798x-6.6)（`openwrt-24.10-6.6` 分支） |
| 目标平台 | `mediatek/filogic`（MT7981，aarch64） |
| 适配机型 | CMCC RAX3000M（仅此一款，不含其它 filogic 机型） |
| 管理地址 | `192.168.6.1` |
| 登录 | 用户名 `root`，密码为空 |
| 默认主题 | Argon |

## 集成插件

| 插件 | 说明 | 上游 |
| --- | --- | --- |
| HomeProxy | 基于 sing-box 1.14 的代理平台，LuCI 可视化配置 | [szwjp/luci-app-homeproxy](https://github.com/szwjp/luci-app-homeproxy) |
| EasyTier | 去中心化组网 / 异地互联，含核心与 LuCI | [EasyTier/luci-app-easytier](https://github.com/EasyTier/luci-app-easytier) |
| ZeroTier | 虚拟局域网 | 官方 feed |
| USB 打印 | `p910nd` 打印服务器 | 官方 feed |
| USB 网卡 | `kmod-usb-net` 及常用驱动 | 官方 feed |
| TTYD | 网页终端 | 官方 feed |
| iPerf3 | 内网测速 | 官方 feed |
| UPnP | 端口自动映射 | 官方 feed |

> 构建时会把 Go 工具链升级到 1.25、sing-box 升级到 1.14.x，以满足 HomeProxy 的版本要求（见 `diy-part2.sh`）。

## 下载与刷机

1. 前往 [Releases](https://github.com/XiaoXinCodes/immortalwrt24.10-6.6-cmcc_rax3000m-237/releases) 下载最新版 `*-sysupgrade.bin`；
2. 在 Breed / U-Boot 下刷入；
3. 首次启动后浏览器打开 `192.168.6.1`，用户名 `root`，密码留空登录。

> 刷机有变砖风险，请确保手头有 Breed 或编程器救砖手段。**首次刷入建议先备份原厂固件 / EEPROM。**

## 自行构建

本仓库使用 GitHub Actions 自动编译，构建流程定义在 [`.github/workflows/openwrt-builder.yml`](.github/workflows/openwrt-builder.yml)。

### 触发构建

- `Actions` → `Build OpenWrt` → `Run workflow`，构建完成后固件自动发布到 Releases，同时保留 Artifacts 备份。

### 自定义固件

| 文件 | 用途 | 执行时机 |
| --- | --- | --- |
| [`.config`](.config) | 编译配置：目标机型、内核模块、插件开关 | feeds 安装后载入 |
| [`diy-part1.sh`](diy-part1.sh) | 添加第三方软件源（如 HomeProxy、EasyTier） | feeds 更新**之前** |
| [`diy-part2.sh`](diy-part2.sh) | 修改默认设置、替换工具链/核心包版本、在 `make defconfig` 前同步插件开关 | feeds 更新**之后** |

改完直接 push，Actions 会自动开始构建。本地想先验证配置：

```bash
git clone https://github.com/padavanonly/immortalwrt-mt798x-6.6 -b openwrt-24.10-6.6 openwrt
cd openwrt
cp /path/to/.config .config
bash /path/to/diy-part1.sh
./scripts/feeds update -a && ./scripts/feeds install -a
bash /path/to/diy-part2.sh
make defconfig
make menuconfig   # 可视化调整
```

### 构建环境说明

GitHub 免费 runner 根盘较小，工作流开头使用 [`easimon/maximize-build-space`](https://github.com/easimon/maximize-build-space) 把构建目录搬到大容量磁盘，解决编译中途磁盘占满的问题。

## 仓库结构

```
.
├── .config                        # 编译配置
├── .github/workflows/
│   ├── openwrt-builder.yml        # 固件构建流水线
│   └── update-checker.yml         # 上游更新检查
├── diy-part1.sh                   # 第三方软件源（feeds 更新前）
├── diy-part2.sh                   # 工具链/默认设置（feeds 更新后）
└── README.md
```

## 致谢

- [P3TERX/Actions-OpenWrt](https://github.com/P3TERX/Actions-OpenWrt) —— 工作流模板
- [padavanonly](https://github.com/padavanonly/immortalwrt-mt798x-6.6) —— mt798x 机型源码维护
- [ImmortalWrt](https://github.com/immortalwrt/immortalwrt) / [OpenWrt](https://github.com/openwrt/openwrt)
- [szwjp](https://github.com/szwjp/luci-app-homeproxy)、[EasyTier](https://github.com/EasyTier/EasyTier)、[sbwml](https://github.com/sbwml/packages_lang_golang)

## 免责声明

本固件仅供学习交流使用。请遵守当地法律法规，代理类插件请勿用于非法用途。因刷机造成的任何设备损坏或数据丢失，作者不承担责任。

## 协议

[MIT](LICENSE)
