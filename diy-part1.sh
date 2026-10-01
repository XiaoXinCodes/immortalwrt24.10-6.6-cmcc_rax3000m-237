#!/bin/bash
#
# Copyright (c) 2019-2020 P3TERX <https://p3terx.com>
#
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#
# https://github.com/P3TERX/Actions-OpenWrt
# File name: diy-part1.sh
# Description: OpenWrt DIY script part 1 (Before Update feeds)
#
set -euo pipefail

# warp must export its headers before automatic build-directory cleanup;
# mt_wifi consumes them later through the target staging directory.
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
patch --batch --fuzz=0 -p1 < "$script_dir/patches/mtk-warp-stage-headers.patch"

# Uncomment a feed source
#sed -i 's/^#\(.*helloworld\)/\1/' feeds.conf.default

# Add a feed source
#echo 'src-git helloworld https://github.com/fw876/helloworld' >>feeds.conf.default
#echo 'src-git passwall https://github.com/xiaorouji/openwrt-passwall' >>feeds.conf.default

# ---------------------------------------------------------------------------
# Third-party packages
# Cloned into package/ and picked up automatically by the build system.
# ---------------------------------------------------------------------------

# HomeProxy: modern proxy platform for ImmortalWrt (sing-box based).
# NOTE: this branch targets sing-box >= 1.14, see diy-part2.sh for the
# matching sing-box / Go toolchain upgrades.
# https://github.com/szwjp/luci-app-homeproxy
git clone --depth 1 https://github.com/szwjp/luci-app-homeproxy package/luci-app-homeproxy

# EasyTier: simple, secure, decentralized mesh VPN (core + LuCI app).
# The 'easytier' core package downloads the official prebuilt binary
# (aarch64 for mt798x) at build time.
# https://github.com/EasyTier/luci-app-easytier
git clone --depth 1 https://github.com/EasyTier/luci-app-easytier package/luci-app-easytier
