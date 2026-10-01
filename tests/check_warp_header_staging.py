#!/usr/bin/env python3
"""Exercise real OpenWrt staging/autoremove rules with the vendor headers.

This checks header delivery, not cross compilation of the kernel modules.
Pass an unmodified source tree matching the workflow's upstream branch.
"""

import argparse
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile


def definition(text, name):
    match = re.search(r'^define ' + re.escape(name) + r'\n.*?^endef$', text, re.M | re.S)
    return match.group(0) if match else ''


def run(*args, **kwargs):
    result = subprocess.run(args, capture_output=True, text=True, **kwargs)
    if result.returncode:
        raise RuntimeError(result.stdout[-2500:] + '\n' + result.stderr[-2500:])
    return result


def check(source):
    repo = Path(__file__).resolve().parents[1]
    core = definition((source / 'include/package.mk').read_text(), 'Build/CoreTargets')
    assert core, 'Missing OpenWrt build rules'
    with tempfile.TemporaryDirectory(prefix='warp-header-check-') as directory:
        root = Path(directory)
        recipe_tree = root / 'recipes'
        for relative in ['package/mtk/drivers/warp/Makefile', 'package/mtk/drivers/mt_wifi/Makefile',
                         'package/mtk/drivers/mt_wifi/patches/005-use-ext-warp-code.patch']:
            destination = recipe_tree / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, destination)
        probe = root / 'probe.c'
        probe.write_text('#include <warp.h>\n#include <warp_wifi.h>\n')
        # The guards skip kernel-only declarations: the probe tests the same
        # vendor include names and search paths without pretending to build a module.
        compiler = ['gcc', '-E', '-P', '-D_WARP_H', '-D_WARP_WIFI_H_']

        for fixed in (False, True):
            if fixed:
                run('patch', '--batch', '--fuzz=0', '-p1', '-i', str(repo / 'patches/mtk-warp-stage-headers.patch'), cwd=recipe_tree)
            work = root / ('fixed' if fixed else 'legacy')
            work.mkdir()
            build = work / 'warp'
            staging = work / 'staging'
            (staging / 'stamp').mkdir(parents=True)
            installed = definition((recipe_tree / 'package/mtk/drivers/warp/Makefile').read_text(), 'Build/InstallDev')
            makefile = work / 'Makefile'
            makefile.write_text(f'''CONFIG_AUTOREMOVE := y
PKG_BUILD_DIR := {build}
PKG_DIR_NAME := warp
STAGING_DIR := {staging}
TMP_DIR := {work / 'tmp'}
SCRIPT_DIR := {source / 'scripts'}
STAMP_PREPARED := {build / '.prepared'}
STAMP_CONFIGURED := {build / '.configured'}
STAMP_BUILT := {build / '.built'}
STAMP_INSTALLED := {staging / 'stamp/.warp_installed'}
STAGING_FILES_LIST := warp.list
TARGET_PATH_PKG := $(PATH)
INSTALL_DIR := install -d
CP := cp -fpR
FIND := find
XARGS := xargs
locked = $(1) true
define Build/Prepare
\t$(CP) {source / 'package/mtk/drivers/warp/src'}/. $(PKG_BUILD_DIR)/
endef
define Build/Compile
\t{' '.join(compiler)} -I$(PKG_BUILD_DIR) {probe} -o {work / 'before-cleanup.i'}
endef
{installed}
{core}
compile: $(STAMP_BUILT)
$(eval $(call Build/CoreTargets))
''')
            run('make', '-f', str(makefile), 'compile', cwd=work)
            assert (work / 'before-cleanup.i').is_file(), 'Headers unavailable even before cleanup'
            assert (build / '.autoremove').exists(), 'Real OpenWrt cleanup did not run'
            assert not (build / 'warp.h').exists(), 'Build directory was not cleaned'

            if fixed:
                driver = work / 'mt_wifi_ap'
                driver.mkdir()
                shutil.copyfile(source / 'package/mtk/drivers/mt_wifi/src/mt_wifi_ap/Makefile', driver / 'Makefile')
                driver_source = source / 'package/mtk/drivers/mt_wifi/src'
                for fragment in driver_source.rglob('*.mk'):
                    copied = work / fragment.relative_to(driver_source)
                    copied.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(fragment, copied)
                run('patch', '--batch', '--fuzz=0', '-p1', '-i', str(recipe_tree / 'package/mtk/drivers/mt_wifi/patches/005-use-ext-warp-code.patch'), cwd=work)
                header_dir = staging / 'usr/include/mtk-warp'
                flags = run('make', '-s', '-f', str(driver / 'Makefile'), 'CONFIG_SUPPORT_OPENWRT=y',
                            'WARP_INCLUDE_DIR=' + str(header_dir),
                            '--eval=print-flags:;@printf "%s" "$(EXTRA_CFLAGS)"', 'print-flags', cwd=work).stdout
                includes = [flag for flag in shlex.split(flags) if flag.startswith('-I' + str(header_dir))]
                assert len(includes) == 2, 'Driver did not consume the staged include paths'
                for header in (source / 'package/mtk/drivers/warp/src').rglob('*.h'):
                    copied = header_dir / header.relative_to(source / 'package/mtk/drivers/warp/src')
                    assert copied.read_bytes() == header.read_bytes(), 'Header content or layout changed'
                run(*compiler, *includes, str(probe), '-o', str(work / 'after-cleanup.i'))
                print('PASS: staged vendor headers remain available after real OpenWrt autoremove')
            else:
                result = subprocess.run([*compiler, '-I' + str(build), str(probe)], capture_output=True, text=True)
                assert result.returncode and 'warp.h: No such file' in result.stderr, result.stderr
                print('REPRODUCED: ' + next(line for line in result.stderr.splitlines() if 'fatal error:' in line))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    check(parser.parse_args().source_dir.resolve())
