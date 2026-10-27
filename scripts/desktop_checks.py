import json
import os
from pathlib import Path
import subprocess
import sys
import time

from mcp_client import Client

root = Path(os.environ['CU_TEST_STATE'])
checks = {}
client = Client(sys.argv[1:])
app = None


def verify(name, condition, detail=None):
    checks[name] = {'passed': bool(condition), 'detail': detail}
    (root / 'checks.json').write_text(json.dumps(checks, indent=2) + '\n')
    print(name, 'PASS' if condition else 'FAIL', json.dumps(detail), flush=True)
    if not condition:
        raise AssertionError(name)


def fixture():
    return json.loads((root / 'fixture-state.json').read_text())


def wait_for(predicate):
    for _ in range(40):
        if predicate():
            return True
        time.sleep(.1)
    return False


try:
    listing = client.rpc('tools/list', {})
    (root / 'tool-schemas.json').write_text(json.dumps(listing, indent=2) + '\n')
    verify('mcp_discovery', len(listing['tools']) >= 15, [t['name'] for t in listing['tools']])
    client.call('setup_accessibility')
    doctor, _ = client.call('doctor')
    (root / 'doctor.json').write_text(json.dumps(doctor, indent=2) + '\n')
    verify('accessibility_enabled', doctor['readiness']['can_build_accessibility_tree'])
    verify('window_backend_ready', doctor['readiness']['can_query_windows'])
    verify('input_backend_ready', doctor['readiness']['can_send_development_input'])
    (root / 'fixture-state.json').unlink(missing_ok=True)
    app = subprocess.Popen(['/usr/bin/python3', str(Path(__file__).with_name('desktop_fixture.py'))],
                           env={**os.environ, 'GTK_MODULES': 'atk-bridge'},
                           stdout=open(root / 'fixture-stdout.log', 'w'),
                           stderr=open(root / 'fixture-stderr.log', 'w'))
    verify('fixture_started', wait_for(lambda: (root / 'fixture-state.json').exists()))
    pid = app.pid
    windows, _ = client.call('list_windows')
    matches = [w for w in windows['windows'] if w.get('pid') == pid]
    verify('window_discovery', len(matches) == 1, matches)
    window_id = matches[0]['window_id']
    if isinstance(window_id, str):
        window_id = int(window_id, 0) if window_id.startswith('0x') else int(window_id)
    client.call('activate_window', {'window_id': window_id})
    focused, _ = client.call('focused_window')
    verify('window_focus', str(pid) in json.dumps(focused), focused)
    state, _ = client.call('get_app_state', {'pid': pid, 'include_screenshot': False})
    nodes = state['accessibility_tree']
    verify('semantic_tree', all(any(n.get('name') == name for n in nodes)
                               for name in ['Compatibility input', 'Compatibility button']),
           {'nodes': len(nodes), 'tree_scoped': state.get('tree_scoped')})
    screen, images = client.call('screenshot', {'full_screen': True, 'format': 'jpeg', 'quality': 35})
    verify('desktop_screenshot', bool(images), screen)
    shot, images = client.call('screenshot', {'window_id': window_id, 'format': 'jpeg', 'quality': 50})
    verify('window_screenshot', bool(images), shot)
    # Full readback proves the semantic text write, independently of dispatch status.
    unicode_text = 'Ubuntu 22.04 — café ✓'
    result, _ = client.call('set_value', {'name': 'Compatibility input', 'value': unicode_text})
    verify('unicode_semantic_text', result.get('verified') is True and
           wait_for(lambda: fixture()['text'] == unicode_text), result)
    result, images = client.call('click', {'name': 'Compatibility button', 'pid': pid,
                                          'include_tree': True, 'screenshot_after': 'window',
                                          'format': 'jpeg', 'quality': 35})
    verify('semantic_button_click', wait_for(lambda: fixture()['clicks'] == 1), result)
    verify('post_action_observation', bool(images) and bool(result.get('accessibility_tree')))
    state, _ = client.call('get_app_state', {'pid': pid, 'include_screenshot': False})
    entry = next(n for n in state['accessibility_tree'] if n.get('name') == 'Compatibility input')
    client.call('click', {'element_index': entry['index'], 'pid': pid})
    client.call('press_key', {'key': 'Ctrl+A', 'window_id': window_id})
    ascii_text = 'Codex X11: Aa09 !@#$%^&*() []{} ' + chr(39) + chr(34) + ' \\ / ?'
    result, _ = client.call('type_text', {'text': ascii_text, 'window_id': window_id,
                                        'include_tree': True})
    verify('targeted_keyboard_text', wait_for(lambda: fixture()['text'] == ascii_text),
           {'expected': ascii_text, 'actual': fixture()['text'], 'backend': result.get('backend')})
    # Pointer click with explicit desktop coordinates, under exact window targeting.
    state, _ = client.call('get_app_state', {'pid': pid, 'include_screenshot': False})
    button = next(n for n in state['accessibility_tree'] if n.get('name') == 'Compatibility button')
    bounds = button['bounds']
    client.call('click', {'x': int(bounds['x'] + bounds['width'] / 2),
                          'y': int(bounds['y'] + bounds['height'] / 2), 'window_id': window_id})
    verify('coordinate_button_click', wait_for(lambda: fixture()['clicks'] == 2))
    state, _ = client.call('get_app_state', {'pid': pid, 'include_screenshot': False})
    node = next(n for n in state['accessibility_tree'] if n.get('name') == 'Compatibility scroll area')
    bounds = node['bounds']
    client.call('scroll', {'direction': 'down', 'pages': 1, 'window_id': window_id,
                           'x': int(bounds['x'] + bounds['width'] / 2),
                           'y': int(bounds['y'] + min(bounds['height'] / 2, 50))})
    verify('scroll_changes_content', wait_for(lambda: fixture()['scroll'] > 0), fixture()['scroll'])
    client.call('move_window', {'window_id': window_id, 'x': 100, 'y': 100})
    client.call('resize_window', {'window_id': window_id, 'width': 620, 'height': 510})
    updated, _ = client.call('list_windows')
    own = next(w for w in updated['windows'] if w.get('pid') == pid)
    verify('window_move_resize', own.get('bounds') != matches[0].get('bounds'), own.get('bounds'))
    state, _ = client.call('get_app_state', {'pid': pid, 'include_screenshot': False})
    drag_nodes = [n for n in state['accessibility_tree'] if n.get('name') == 'Compatibility drag area']
    if drag_nodes:
        bounds = drag_nodes[0]['bounds']
        client.call('drag', {'start_x': int(bounds['x'] + 30), 'start_y': int(bounds['y'] + 25),
                             'end_x': int(bounds['x'] + 140), 'end_y': int(bounds['y'] + 25)})
        verify('drag_delivery', wait_for(lambda: fixture()['drags'] == 1))
    else:
        verify('drag_area_present', False)
    checks['all_passed'] = True
    (root / 'checks.json').write_text(json.dumps(checks, indent=2) + '\n')
finally:
    if app is not None:
        app.terminate()
        try:
            app.wait(timeout=5)
        except subprocess.TimeoutExpired:
            app.kill()
            app.wait()
    client.close()
    try:
        old = json.loads((root / 'before.json').read_text())['focused_window']
        subprocess.run(['xdotool', 'windowactivate', '--sync', old], timeout=3,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
