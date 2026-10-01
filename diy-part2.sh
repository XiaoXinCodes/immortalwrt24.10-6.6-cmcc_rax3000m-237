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
set -euo pipefail

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
package_upgrade_dir=$(mktemp -d)
trap 'rm -rf "$package_upgrade_dir"' EXIT
git clone --depth 1 --single-branch -b 25.x https://github.com/sbwml/packages_lang_golang "$package_upgrade_dir/golang"

# sing-box 1.14.x (upstream OpenWrt packaging): required by
# luci-app-homeproxy's 1.14 config format; the 24.10 feed ships 1.12.x.
# https://github.com/openwrt/packages/tree/master/net/sing-box
# GitHub no longer supports SVN export. Fetch the reviewed recipe with native
# Git, checking out only this package and keeping its upstream source hash.
sing_box_recipe_rev=95d73ebcc95ade2ea78b0a281898cf8b6ec7b7f9
git init -q "$package_upgrade_dir/packages"
git -C "$package_upgrade_dir/packages" remote add origin https://github.com/openwrt/packages
git -C "$package_upgrade_dir/packages" sparse-checkout init --cone
git -C "$package_upgrade_dir/packages" sparse-checkout set net/sing-box
git -C "$package_upgrade_dir/packages" fetch --depth 1 --filter=blob:none origin "$sing_box_recipe_rev"
git -C "$package_upgrade_dir/packages" checkout --detach FETCH_HEAD
test -f "$package_upgrade_dir/packages/net/sing-box/Makefile"

# This older buildroot generates a Kconfig cycle when the tiny variant provides
# the full package and conflicts with it. Keep both explicit packages, but make
# HomeProxy's +sing-box dependency resolve directly to the full variant.
sed -i '/^[[:space:]]*PROVIDES:=sing-box$/d' "$package_upgrade_dir/packages/net/sing-box/Makefile"

# Replace installed feed recipes only after both downloads have succeeded.
rm -rf feeds/packages/lang/golang feeds/packages/net/sing-box
mv "$package_upgrade_dir/golang" feeds/packages/lang/golang
cp -a "$package_upgrade_dir/packages/net/sing-box" feeds/packages/net/sing-box

# The current feed's unused PassWall menu has a separate recursive dependency.
# Omit its installed feed link for this HomeProxy build. An explicitly selected
# PassWall is retained so strict defconfig reports the issue instead of silently
# removing a requested feature.
if ! grep -Eq '^CONFIG_PACKAGE_luci-app-passwall=[ym]$' .config; then
  if [ -L package/feeds/luci/luci-app-passwall ]; then
    rm package/feeds/luci/luci-app-passwall
  fi
fi

# ---------------------------------------------------------------------------
# .config plugin selection (enforced here, before `make defconfig`)
# The repo-root .config carries the same selection; enforcing it here keeps
# the build correct even if the .config was regenerated via menuconfig.
# ---------------------------------------------------------------------------
# Drop OpenClash (no such package in this source tree; `make defconfig`
# would silently discard the symbol anyway) and enable HomeProxy + EasyTier.
sed -i 's/^CONFIG_PACKAGE_luci-app-openclash=y/# CONFIG_PACKAGE_luci-app-openclash is not set/' .config
for package in luci-app-homeproxy easytier luci-app-easytier sing-box; do
  sed -i "/^CONFIG_PACKAGE_${package}=/d; /^# CONFIG_PACKAGE_${package} is not set$/d" .config
  echo "CONFIG_PACKAGE_${package}=y" >> .config
done
sed -i '/^CONFIG_PACKAGE_sing-box-tiny=/d; /^# CONFIG_PACKAGE_sing-box-tiny is not set$/d' .config
echo '# CONFIG_PACKAGE_sing-box-tiny is not set' >> .config
