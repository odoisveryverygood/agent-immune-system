"""Start the local UI and backend; credentials stay in the backend environment."""
import argparse
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--state-path', default='.state/runs.sqlite3')
    parser.add_argument('--api-port', type=int, default=8011)
    parser.add_argument('--ui-port', type=int, default=5175)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    backend_env = dict(os.environ)
    for line in args.env_file.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        key, separator, value = line.partition('=')
        if separator and re.fullmatch(r'[A-Z_][A-Z0-9_]*', key.strip()):
            backend_env[key.strip()] = value.strip().strip('"').strip("'")
    backend_env['IMMUNE_STATE_PATH'] = str(Path(args.state_path).resolve())
    backend_env.setdefault('CRUSOE_MODEL', 'deepseek-ai/Deepseek-V4-Flash')
    backend_env.setdefault('NEMOTRON_MODEL', 'nvidia/Nemotron-3.5-Lightning-30B-A3B')
    required = ('CRUSOE_API_KEY', 'YOU_API_KEY', 'IMMUNE_SANDBOX_ID', 'IMMUNE_OPENSHELL_GATEWAY')
    missing = [key for key in required if not backend_env.get(key)]
    if missing:
        parser.error('Missing backend configuration: ' + ', '.join(missing))
    frontend_env = {key: value for key, value in os.environ.items() if key not in required}
    frontend_env['API_PROXY_TARGET'] = f'http://127.0.0.1:{args.api_port}'
    children = []
    try:
        children.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.api.app:app', '--host', '127.0.0.1', '--port', str(args.api_port)], cwd=root, env=backend_env, start_new_session=True))
        children.append(subprocess.Popen(['npm', 'run', 'dev', '--', '--port', str(args.ui_port), '--strictPort'], cwd=root / 'frontend', env=frontend_env, start_new_session=True))
        print(f'Demo UI: http://127.0.0.1:{args.ui_port} — choose Live models, then Recovery drill.', flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(.5)
    except KeyboardInterrupt:
        pass
    finally:
        for child in children:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()


if __name__ == '__main__':
    main()
