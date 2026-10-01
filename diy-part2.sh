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

# Resolve the latest official stable sing-box release on every build, then
# choose a sbwml Go recipe satisfying that release's go.mod/toolchain directive.
package_upgrade_dir=$(mktemp -d)
trap 'rm -rf "$package_upgrade_dir"' EXIT
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
python3 "$script_dir/scripts/update-proxy-packages.py" --build-dir "$PWD" --staging-dir "$package_upgrade_dir"

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
