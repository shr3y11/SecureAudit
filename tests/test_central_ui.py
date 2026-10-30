"""Execute the actual dashboard renderers with a minimal DOM in Node.

This checks integrity-state presentation; it is not a browser layout test.
"""
from pathlib import Path
import shutil
import subprocess

import pytest


def test_integrity_failure_is_visible_and_does_not_look_like_zero_risk():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is needed to execute dashboard renderers")
    source = Path(__file__).resolve().parents[1] / "secureaudit_central/static/app.js"
    harness = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const elements = new Map();
const document = {getElementById(id) {
  if (!elements.has(id)) elements.set(id, {value: id === 'search' ? '' : 'all',
    classList: {toggle() {}}, setAttribute() {}, addEventListener() {}});
  return elements.get(id);
}, querySelectorAll() {return []}};
const context = vm.createContext({document, location: {hash: ''},
  sessionStorage: {getItem() {return ''}}, URLSearchParams});
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), context);
vm.runInContext(`
const fixture = {endpoint_count: 1, simulated_count: 0, assessed_endpoints: 1,
  passed: 1, failed: 0, errors: 0, score: null, coverage: null,
  at_risk_endpoints: 0, integrity_ok: false};
renderStats(fixture);
endpoints = [{id:'id', hostname:'host', group_name:'lab', latest:fixture}];
renderEndpoints();
showAssessment({...fixture, checks:[]});
`, context);
assert.strictEqual(elements.get('score').textContent, '—');
assert.strictEqual(elements.get('risk').textContent, '—');
assert.match(elements.get('risk-stat').textContent, /integrity failed/);
assert.match(elements.get('endpoint-rows').innerHTML, /Integrity check failed/);
assert.match(elements.get('endpoint-rows').innerHTML, /score-bad/);
assert.match(elements.get('assessment-body').innerHTML, /readings below are unverified/);
vm.runInContext('renderStats({...fixture, integrity_ok:true, score:100, coverage:100})', context);
assert.strictEqual(elements.get('score').textContent, '100.0%');
assert.strictEqual(elements.get('risk').textContent, 0);
'''
    subprocess.run([node, "-e", harness, str(source)], check=True, capture_output=True, text=True)
