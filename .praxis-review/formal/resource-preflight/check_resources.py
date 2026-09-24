import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path.cwd()
canonical = Path('/home/che/dev/go2-workspace/current/.substrate')
evidence = Path(os.environ['PRAXIS_EVIDENCE_DIR']) / 'formal' / 'resource-preflight'
task = json.loads((root / 'tools/substrate/tasks/rl_shared_transfer_combination_v1.json').read_text())
protocol_path = root / task['protocol']
protocol = json.loads(protocol_path.read_text())
reference_lock = json.loads((root / 'tools/substrate/rl_reference.lock.json').read_text())
source_lock = json.loads((root / 'tools/substrate/sources.lock.json').read_text())

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

checkpoint = canonical / 'rl' / 'policy.pt'
checkpoint_actual = sha(checkpoint) if checkpoint.is_file() else None
upstream = canonical / 'upstream-go2-30e74dc5'
source_results = []
for name, expected in sorted(reference_lock['files'].items()):
    path = upstream / name
    actual = sha(path) if path.is_file() else None
    source_results.append({'path': name, 'expected_sha256': expected, 'actual_sha256': actual, 'pass': actual == expected})
interpreter = canonical / 'venv-reliable' / 'bin' / 'python'
code = r'''import json, os, sys, torch, mujoco, numpy as np
from pathlib import Path
from tools.substrate.environment import verify_environment
prefix = Path(sys.prefix).resolve()
modules = {"torch": {"version": torch.__version__, "path": str(Path(torch.__file__).resolve())}, "mujoco": {"version": mujoco.__version__, "path": str(Path(mujoco.__file__).resolve())}, "numpy": {"version": np.__version__, "path": str(Path(np.__file__).resolve())}}
expected = {"torch": "2.6.0+cpu", "mujoco": "3.3.6", "numpy": "2.2.6"}
for name, version in expected.items():
    if modules[name]["version"] != version:
        raise SystemExit(f"{name} version mismatch: {modules[name]['version']!r}")
    if not Path(modules[name]["path"]).is_relative_to(prefix):
        raise SystemExit(f"{name} imported outside venv")
report = verify_environment()
print(json.dumps({"sys_executable": sys.executable, "sys_prefix": sys.prefix, "modules": modules, "verify_environment": report}, sort_keys=True))'''
env = os.environ.copy()
env.pop('PYTHONPATH', None)
env['PYTHONNOUSERSITE'] = '1'
env['PYTHONDONTWRITEBYTECODE'] = '1'
run = subprocess.run([str(interpreter), '-c', code], cwd=root, env=env, capture_output=True, text=True)
(evidence / 'reliable-imports.stdout').write_text(run.stdout)
(evidence / 'reliable-imports.stderr').write_text(run.stderr)
header = Path('/home/che/.mujoco/mujoco-3.3.6/include/mujoco/mujoco.h')
library = Path('/home/che/.mujoco/mujoco-3.3.6/lib/libmujoco.so')
native = canonical / 'headless-reliable' / 'go2_mjpc_admit'
checks = {
    'task_protocol_sha256': {'expected': task['protocol_sha256'], 'actual': sha(protocol_path), 'pass': sha(protocol_path) == task['protocol_sha256']},
    'checkpoint_sha256': {'expected': protocol['source_identity']['checkpoint_sha256'], 'actual': checkpoint_actual, 'pass': checkpoint_actual == protocol['source_identity']['checkpoint_sha256'] == source_lock['rl']['sha256']},
    'source_commit': {'expected': protocol['source_identity']['commit'], 'reference_lock': reference_lock['commit'], 'pass': protocol['source_identity']['commit'] == reference_lock['commit'] == source_lock['rl']['commit']},
    'upstream_files': {'count': len(source_results), 'all_pass': bool(source_results) and all(item['pass'] for item in source_results), 'files': source_results},
    'reliable_interpreter': {'path': str(interpreter), 'exists': interpreter.is_file() and os.access(interpreter, os.X_OK), 'returncode': run.returncode, 'pass': run.returncode == 0},
    'mjpc_admission_binary': {'path': str(native), 'exists': native.is_file(), 'executable': native.is_file() and os.access(native, os.X_OK), 'pass': native.is_file() and os.access(native, os.X_OK)},
    'mujoco_sdk_header': {'path': str(header), 'exists': header.is_file(), 'pass': header.is_file()},
    'mujoco_sdk_library': {'path': str(library), 'exists': library.exists(), 'resolved': str(library.resolve()) if library.exists() else None, 'pass': library.is_file()},
}
checks['pass'] = all([
    checks['task_protocol_sha256']['pass'], checks['checkpoint_sha256']['pass'], checks['source_commit']['pass'],
    checks['upstream_files']['all_pass'], checks['reliable_interpreter']['pass'], checks['mjpc_admission_binary']['pass'],
    checks['mujoco_sdk_header']['pass'], checks['mujoco_sdk_library']['pass']])
(evidence / 'resource-preflight.json').write_text(json.dumps(checks, indent=2, sort_keys=True) + '\n')
print(json.dumps({k: v for k, v in checks.items() if k != 'upstream_files'}, indent=2, sort_keys=True))
print(f"upstream_file_count={len(source_results)} all_pass={checks['upstream_files']['all_pass']}")
if run.stdout:
    print('reliable_imports=' + run.stdout.strip())
if run.stderr:
    print('reliable_imports_stderr=' + run.stderr.strip())
sys.exit(0 if checks['pass'] else 1)
