"""Small persistent JSON-RPC client for testing the actual stdio MCP server."""
import json
import os
from pathlib import Path
import select
import subprocess
import time


class Client:
    def __init__(self, command):
        self.directory = Path(os.environ['CU_TEST_STATE'])
        self.directory.mkdir(parents=True, exist_ok=True)
        self.directory.chmod(0o700)
        self.log = open(self.directory / 'mcp-stderr.log', 'a')
        self.proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self.log, text=True, bufsize=1)
        self.number = 0
        self.results = []
        self.rpc('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {},
                               'clientInfo': {'name': 'CodexCompatibilityTest', 'version': '1'}})
        self.proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized'}) + '\n')
        self.proc.stdin.flush()

    def rpc(self, method, params):
        self.number += 1
        request = {'jsonrpc': '2.0', 'id': self.number, 'method': method, 'params': params}
        self.proc.stdin.write(json.dumps(request) + '\n')
        self.proc.stdin.flush()
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if not select.select([self.proc.stdout], [], [], 1)[0]:
                if self.proc.poll() is not None:
                    raise RuntimeError('MCP exited: %s' % self.proc.returncode)
                continue
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError('MCP closed stdout')
            response = json.loads(line)
            if response.get('id') == self.number:
                if 'error' in response:
                    raise RuntimeError(response['error'])
                return response['result']
        raise TimeoutError(method)

    def call(self, name, arguments=None, allow_error=False):
        result = self.rpc('tools/call', {'name': name, 'arguments': arguments or {}})
        report = result.get('structuredContent')
        if report is None:
            for block in result.get('content', []):
                if block.get('type') == 'text':
                    try:
                        report = json.loads(block['text'])
                        break
                    except ValueError:
                        continue
        images = []
        for block in result.get('content', []):
            if block.get('type') == 'image':
                images.append({'mimeType': block['mimeType'], 'encoded_bytes': len(block['data'])})
        self.results.append({'tool': name, 'arguments': arguments or {}, 'report': report,
                             'images': images, 'isError': result.get('isError', False)})
        self.save()
        if result.get('isError') and not allow_error:
            raise RuntimeError('%s: %s' % (name, report or result))
        return report, images

    def save(self):
        (self.directory / 'mcp-results.json').write_text(json.dumps(self.results, indent=2) + '\n')

    def close(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        self.log.close()
