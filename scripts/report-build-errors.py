#!/usr/bin/env python3
"""Publish failed OpenWrt targets' compiler errors as Actions annotations."""

import argparse
from collections import deque
import os
from pathlib import Path
import re


def escape(text):
    return text.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')


def error_context(path):
    previous = deque(maxlen=4)
    contexts = []
    pattern = re.compile(r'\berror:|fatal:|undefined reference|No such file|No space left|Killed signal|make(?:\[\d+\])?: \*\*\*', re.I)
    with path.open(errors='replace') as stream:
        for line in stream:
            if pattern.search(line):
                contexts.append(''.join(previous) + line)
                if len(contexts) == 3:
                    break
            previous.append(line)
    if contexts:
        return '\n'.join(contexts)[-6000:]
    with path.open(errors='replace') as stream:
        return ''.join(deque(stream, maxlen=35))[-6000:]


def report(build, console):
    targets = []
    with console.open(errors='replace') as stream:
        for line in stream:
            match = re.search(r'ERROR: ((?:package|tools|toolchain|target)/[\w./+-]+).*failed to build', line)
            if match and '..' not in Path(match.group(1)).parts and match.group(1) not in targets:
                targets.append(match.group(1))
    summaries = []
    for target in targets[:8]:
        folder = build / 'logs' / target
        logs = sorted(path for path in folder.rglob('*compile.txt') if not path.name.startswith('check-'))
        for log in logs[:2]:
            context = error_context(log)
            print('::error title=' + target + '::' + escape(context), flush=True)
            summaries.append('### ' + target + '\n\n```text\n' + context + '\n```\n')
    if not summaries:
        context = error_context(console)
        print('::error title=Firmware build failed::' + escape(context), flush=True)
        summaries.append('```text\n' + context + '\n```\n')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
            stream.write('\n'.join(summaries))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', type=Path, required=True)
    parser.add_argument('--console-log', type=Path, required=True)
    args = parser.parse_args()
    report(args.build_dir, args.console_log)
