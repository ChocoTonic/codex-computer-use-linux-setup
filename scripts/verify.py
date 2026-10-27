#!/usr/bin/env python3
"""Verify MCP startup; optionally exercise a disposable window on the desktop."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--launcher', type=Path, default=Path.home()/'.local/bin/computer-use-linux')
    parser.add_argument('--desktop', action='store_true', help='Test screenshots, input, scrolling, and drag in a disposable GTK window')
    parser.add_argument('--enable-accessibility', action='store_true', help='Enable saved/runtime AT-SPI for this user')
    parser.add_argument('--state-dir', type=Path, help='Private directory for test results (may contain desktop metadata)')
    args = parser.parse_args()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    state = args.state_dir or Path.home()/'.local/state/codex-computer-use-linux/verification'/stamp
    state.mkdir(parents=True, exist_ok=True)
    state.chmod(0o700)
    os.environ['CU_TEST_STATE'] = str(state.absolute())
    os.environ.setdefault('DISPLAY', ':0')
    os.environ.setdefault('XAUTHORITY', str(Path.home()/'.Xauthority'))
    os.environ.setdefault('XDG_RUNTIME_DIR', '/run/user/' + str(os.getuid()))
    os.environ.setdefault('DBUS_SESSION_BUS_ADDRESS', 'unix:path=' + os.environ['XDG_RUNTIME_DIR'] + '/bus')
    os.environ['PATH'] = str(args.launcher.absolute().parent) + ':' + os.environ['PATH']
    os.environ['XDG_SESSION_TYPE'] = 'x11'
    os.environ['XDG_CURRENT_DESKTOP'] = 'LXQt'
    from mcp_client import Client
    client = Client([str(args.launcher.absolute()), 'mcp'])
    try:
        tools = client.rpc('tools/list', {})['tools']
        expected = {'get_app_state', 'screenshot', 'type_text', 'click', 'drag', 'list_windows'}
        assert expected <= {t['name'] for t in tools}, 'Required MCP tools missing'
        print('MCP startup: PASS (' + str(len(tools)) + ' tools)')
        if args.enable_accessibility:
            result, _ = client.call('setup_accessibility')
            print('Accessibility setup:', result.get('message'))
        doctor, _ = client.call('doctor')
        readiness = doctor['readiness']
        (state/'doctor.json').write_text(json.dumps(doctor, indent=2)+'\n')
        print(json.dumps(readiness, indent=2))
        if readiness['blockers']:
            raise RuntimeError('Readiness blockers remain. Review doctor.json.')
    finally:
        client.close()
    if args.desktop:
        if not args.enable_accessibility:
            # desktop_checks calls setup_accessibility; require explicit consent for that change.
            raise ValueError('--desktop also requires --enable-accessibility')
        focus = subprocess.check_output(['xdotool', 'getwindowfocus'], text=True).strip()
        (state/'before.json').write_text(json.dumps({'focused_window': focus}))
        log = state/'desktop-checks.log'
        with log.open('w') as output:
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('desktop_checks.py')),
                                     str(args.launcher.absolute()), 'mcp'], stdout=output, stderr=subprocess.STDOUT)
        checks = json.loads((state/'checks.json').read_text()) if (state/'checks.json').exists() else {}
        passed = sum(isinstance(v, dict) and v.get('passed', False) for v in checks.values())
        print('Desktop checks passed:', passed)
        if result.returncode or not checks.get('all_passed'):
            raise RuntimeError('Desktop verification failed. Inspect ' + str(log))
    print('Private verification results:', state)
    print('Verification passed. Start a fresh Codex session to load this MCP entry.')


if __name__ == '__main__':
    os.umask(0o077)
    try:
        main()
    except (AssertionError, RuntimeError, ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
