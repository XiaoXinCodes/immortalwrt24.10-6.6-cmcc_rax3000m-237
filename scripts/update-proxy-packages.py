#!/usr/bin/env python3
"""Resolve the latest stable sing-box release and a compatible OpenWrt Go feed."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import urllib.parse
import urllib.request


def git(*args):
    return subprocess.check_output(["git", *map(str, args)], text=True).strip()


def fetch(url):
    headers = {"User-Agent": "OpenWrt-proxy-package-updater"}
    if urllib.parse.urlparse(url).hostname == "api.github.com":
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = "Bearer " + token
        headers["Accept"] = "application/vnd.github+json"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=90) as response:
        return response.read()


def api(path):
    return json.loads(fetch("https://api.github.com/repos/" + path))


def version(text):
    if not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", text):
        raise ValueError("Invalid stable version: " + text)
    parts = tuple(map(int, text.split(".")))
    return parts + (0,) * (3 - len(parts))


def required_go(go_mod):
    minimum = re.search(r"^go (\d+\.\d+(?:\.\d+)?)\s*$", go_mod, re.M)
    if not minimum:
        raise ValueError("Released go.mod has no Go version requirement")
    versions = [minimum.group(1)]
    toolchain = re.search(r"^toolchain go(\d+\.\d+(?:\.\d+)?)\s*$", go_mod, re.M)
    if toolchain:
        versions.append(toolchain.group(1))
    return max(versions, key=version)


def go_recipe_version(recipe):
    major_minor = re.search(r"^GO_VERSION_MAJOR_MINOR\s*:?=\s*(\d+\.\d+)\s*$", recipe, re.M)
    patch = re.search(r"^GO_VERSION_PATCH\s*:?=\s*(\d+)\s*$", recipe, re.M)
    if not major_minor or not patch:
        raise ValueError("Unsupported Go recipe version format")
    return major_minor.group(1) + "." + patch.group(1)


def set_make_value(recipe, name, value):
    result, count = re.subn(r"^" + re.escape(name) + r"\s*:?=.*$", name + ":=" + value, recipe, flags=re.M)
    if count != 1:
        raise ValueError("Expected one " + name + " field in the upstream recipe")
    return result


def choose_go_recipe(go_repo, staging, minimum_go):
    branches = sorted({int(m.group(1)) for m in re.finditer(r"refs/heads/(\d+)\.x$", git("ls-remote", "--heads", go_repo), re.M)})
    major, minor, _ = version(minimum_go)
    if major != 1:
        raise ValueError("Unsupported Go major version: " + minimum_go)
    for candidate in branches:
        if candidate < minor:
            continue
        go_dir = staging / ("golang-" + str(candidate))
        git("clone", "--depth", "1", "--single-branch", "--branch", str(candidate) + ".x", go_repo, go_dir)
        actual_go = go_recipe_version((go_dir / "golang/Makefile").read_text())
        if version(actual_go) >= version(minimum_go):
            return go_dir, actual_go, str(candidate) + ".x"
        print("Skipping Go " + actual_go + ": below " + minimum_go, flush=True)
        shutil.rmtree(go_dir)
    raise ValueError("No maintained Go recipe satisfies " + minimum_go + "; refusing to build an older sing-box")


def prepare(build, staging):
    release = api("SagerNet/sing-box/releases/latest")
    tag = release["tag_name"]
    if release.get("draft") or release.get("prerelease") or not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise ValueError("Latest release is not a stable sing-box version")
    release_version = tag[1:]
    commit = api("SagerNet/sing-box/commits/" + tag)["sha"]
    # Read the same immutable release commit for dependency discovery.
    go_mod = base64.b64decode(api("SagerNet/sing-box/contents/go.mod?ref=" + commit)["content"]).decode()
    minimum_go = required_go(go_mod)
    print("Latest stable sing-box: " + release_version + "; required Go >= " + minimum_go, flush=True)

    packages = staging / "packages"
    git("clone", "--depth", "1", "--single-branch", "--branch", "master", "--filter=blob:none", "--sparse",
        "https://github.com/openwrt/packages", packages)
    git("-C", packages, "sparse-checkout", "set", "net/sing-box")
    recipe_path = packages / "net/sing-box/Makefile"
    recipe = recipe_path.read_text()
    if "https://codeload.github.com/SagerNet/sing-box/tar.gz/v$(PKG_VERSION)?" not in recipe:
        raise ValueError("Upstream sing-box source URL format changed; refusing an inconsistent source/hash update")

    download_dir = build / "dl"
    download_dir.mkdir(exist_ok=True)
    source_name = "sing-box-" + release_version + ".tar.gz"
    source = staging / source_name
    source.write_bytes(fetch("https://codeload.github.com/SagerNet/sing-box/tar.gz/" + tag))
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    with tarfile.open(source) as archive:
        member = archive.extractfile("sing-box-" + release_version + "/go.mod")
        if member is None or member.read().decode() != go_mod:
            raise ValueError("Release archive go.mod does not match the resolved release commit")
    # This is a new release's checksum, obtained from its official HTTPS archive;
    # OpenWrt still verifies PKG_HASH on all subsequent downloads/cache restores.
    recipe = set_make_value(recipe, "PKG_VERSION", release_version)
    recipe = set_make_value(recipe, "PKG_HASH", source_hash)
    # The older metadata generator cannot handle this conflicting virtual alias.
    # Both full and tiny packages remain available explicitly.
    recipe = re.sub(r"^\s*PROVIDES\s*:?=\s*sing-box[ \t]*$", "", recipe, flags=re.M)
    recipe_path.write_text(recipe)

    go_repo = "https://github.com/sbwml/packages_lang_golang"
    go_dir, actual_go, branch = choose_go_recipe(go_repo, staging, minimum_go)
    manifest = {
        "sing_box_version": release_version,
        "sing_box_commit": commit,
        "sing_box_source_sha256": source_hash,
        "sing_box_recipe_commit": git("-C", packages, "rev-parse", "HEAD"),
        "required_go": minimum_go,
        "selected_go": actual_go,
        "go_branch": branch,
        "go_recipe_commit": git("-C", go_dir, "rev-parse", "HEAD"),
    }
    # All discovery/validation must succeed before replacing installed recipes.
    go_destination = build / "feeds/packages/lang/golang"
    sing_destination = build / "feeds/packages/net/sing-box"
    if not go_destination.is_dir() or not sing_destination.is_dir():
        raise ValueError("Run this updater after feeds update/install in an OpenWrt tree")
    shutil.rmtree(go_destination)
    shutil.rmtree(sing_destination)
    shutil.move(str(go_dir), go_destination)
    shutil.copytree(packages / "net/sing-box", sing_destination)
    shutil.copyfile(source, download_dir / source_name)
    (build / "proxy-package-versions.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--staging-dir", type=Path, required=True)
    arguments = parser.parse_args()
    prepare(arguments.build_dir.resolve(), arguments.staging_dir.resolve())
