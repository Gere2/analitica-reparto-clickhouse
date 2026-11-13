"""Exercise actual Bash control flow with fake API/export calls, never Docker or a real run."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/simulation_watchdog.sh'
RUN = '4f297d43-7255-4c72-8b4d-0dc108280f6c'


@unittest.skipUnless(shutil.which('bash'), 'Watchdog requires Bash')
class WatchdogTests(unittest.TestCase):
    def run_case(self, overrides, command='check_api 8001 hybrid'):
        with tempfile.TemporaryDirectory() as folder:
            program = r'''
source "$WATCHDOG_SCRIPT"
PAUSE="$CASE_DIR/pause"; RESERVE_PENDING="$CASE_DIR/reserve-pending"
TARGETS=8001:hybrid; DRAIN_TIMEOUT_SECONDS=0
python() { command "$PYTHON_TEST_EXEC" "$@"; }
free_gb() { echo 100; }
curl() {
  case "$*" in
    *simulation/start*) echo START >> "$CASE_DIR/actions"; echo '{"running":true,"run_id":"11111111-1111-4111-8111-111111111111"}' ;;
    *simulation/stop*) echo '{"running":false,"run_id":"4f297d43-7255-4c72-8b4d-0dc108280f6c"}' ;;
    *api/simulation*) echo '{"running":false,"run_id":"4f297d43-7255-4c72-8b4d-0dc108280f6c"}' ;;
    *api/status*) echo '{"pending":0}' ;;
    *) return 1 ;;
  esac
}
save_run() { echo EXPORT >> "$CASE_DIR/actions"; return 0; }
'''
            result = subprocess.run(['bash', '-c', program + '\n' + overrides + '\n' + command],
                env={**os.environ, 'WATCHDOG_SCRIPT': str(SCRIPT), 'CASE_DIR': folder,
                     'PYTHON_TEST_EXEC': sys.executable},
                capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            actions = Path(folder) / 'actions'
            return actions.read_text().splitlines() if actions.exists() else [], Path(folder, 'pause').exists(), Path(folder, 'reserve-pending').exists()

    def test_only_a_drained_verified_unchanged_run_can_restart(self):
        actions, _, _ = self.run_case('')
        self.assertEqual(actions, ['EXPORT', 'START'])

    def test_pending_or_unknown_queue_cannot_export_or_restart(self):
        for response in ('{"pending":1}', '{}', '{"pending":"0"}'):
            override = "queue_zero() { printf '%s' '" + response + "' | python -c 'import json,sys; v=json.load(sys.stdin).get(\"pending\"); sys.exit(0 if type(v) is int and v == 0 else 1)'; }"
            with self.subTest(response=response): self.assertEqual(self.run_case(override)[0], [])

    def test_failed_export_blocks_restart(self):
        self.assertEqual(self.run_case('save_run() { return 1; }')[0], [])

    def test_maintenance_pause_arriving_during_export_blocks_restart(self):
        actions, paused, _ = self.run_case('save_run() { touch "$PAUSE"; echo EXPORT >> "$CASE_DIR/actions"; }')
        self.assertEqual(actions, ['EXPORT']); self.assertTrue(paused)

    def test_manual_restart_during_export_is_not_replaced(self):
        override = r'''
save_run() { touch "$CASE_DIR/changed"; echo EXPORT >> "$CASE_DIR/actions"; }
curl() {
 case "$*" in
  *api/status*) echo '{"pending":0}' ;;
  *simulation/start*) echo START >> "$CASE_DIR/actions" ;;
  *api/simulation*) if [ -e "$CASE_DIR/changed" ]; then echo '{"running":true}'; else echo '{"running":false,"run_id":"4f297d43-7255-4c72-8b4d-0dc108280f6c"}'; fi ;;
 esac
}
'''
        self.assertEqual(self.run_case(override)[0], ['EXPORT'])

    def test_disk_reserve_keeps_incomplete_stop_export_paused_for_retry(self):
        _, paused, pending = self.run_case('save_run() { return 1; }', 'reserve_reached 1')
        self.assertTrue(paused and pending)
        _, paused, pending = self.run_case('', 'reserve_reached 1')
        self.assertTrue(paused); self.assertFalse(pending)

    def test_unreadable_disk_reserve_blocks_a_new_run(self):
        self.assertEqual(self.run_case('free_gb() { return 1; }')[0], ['EXPORT'])


if __name__ == '__main__': unittest.main()
