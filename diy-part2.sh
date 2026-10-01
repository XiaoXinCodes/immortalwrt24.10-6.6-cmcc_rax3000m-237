#!/bin/bash
#
# Copyright (c) 2019-2020 P3TERX <https://p3terx.com>
#
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#
# https://github.com/P3TERX/Actions-OpenWrt
# File name: diy-part2.sh
# Description: OpenWrt DIY script part 2 (After Update feeds)
#

# Modify default IP
#sed -i 's/192.168.1.1/192.168.6.1/g' package/base-files/files/bin/config_generate

# ---------------------------------------------------------------------------
# Toolchain / core package upgrades
# Runs after feeds are updated & installed, so feed directories can be
# replaced in place (existing package/feeds symlinks keep working).
# ---------------------------------------------------------------------------

# Go 1.25 (sbwml backport): sing-box >= 1.14 requires Go >= 1.25,
# while the 24.10 feed ships Go 1.23.
# https://github.com/sbwml/packages_lang_golang
rm -rf feeds/packages/lang/golang
git clone --depth 1 -b 25.x https://github.com/sbwml/packages_lang_golang feeds/packages/lang/golang

# sing-box 1.14.x (upstream OpenWrt packaging): required by
# luci-app-homeproxy's 1.14 config format; the 24.10 feed ships 1.12.x.
# https://github.com/openwrt/packages/tree/master/net/sing-box
rm -rf feeds/packages/net/sing-box
svn export --force https://github.com/openwrt/packages/trunk/net/sing-box feeds/packages/net/sing-box

# ---------------------------------------------------------------------------
# .config plugin selection (enforced here, before `make defconfig`)
# The repo-root .config carries the same selection; enforcing it here keeps
# the build correct even if the .config was regenerated via menuconfig.
# ---------------------------------------------------------------------------
# Drop OpenClash (no such package in this source tree; `make defconfig`
# would silently discard the symbol anyway) and enable HomeProxy + EasyTier.
sed -i 's/^CONFIG_PACKAGE_luci-app-openclash=y/# CONFIG_PACKAGE_luci-app-openclash is not set/' .config
sed -i 's/^# CONFIG_PACKAGE_luci-app-homeproxy is not set/CONFIG_PACKAGE_luci-app-homeproxy=y/' .config
grep -q '^CONFIG_PACKAGE_easytier=y' .config || echo 'CONFIG_PACKAGE_easytier=y' >> .config
grep -q '^CONFIG_PACKAGE_luci-app-easytier=y' .config || echo 'CONFIG_PACKAGE_luci-app-easytier=y' >> .config