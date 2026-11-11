"""P3-08 regression: synthetic-only orchestration and failure states.

For full original snapshot/archive/catalog proof run scripts.recovery_review_gate
on an authorized complete checkout. Mocks here test the control-flow contract.
"""
from contextlib import redirect_stdout
import hashlib
import io
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from scripts import recovery_review_gate as gate
from dbvora.archive.request_service import RequestServiceError
from dbvora.archive.review_html import render


class RecoveryReviewGateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='dbvora-review-orchestrator-test-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)

    def simulate(self, *, codec='zip', fail_replay=False, ignore_corruption=False,
                 change_source=False):
        published = {}
        archive_sha = {}
        def fake_snapshot(source, dest):
            path = dest / ('dbvora-' + '0'*32 + '.sqlite')
            shutil.copyfile(source, path)
            return {'snapshot_path': str(path)}
        def fake_archive(snapshot, destination, ledger, request, **kwargs):
            if 'file' in published:
                if fail_replay:
                    return {'status': 'RECORDED_UNVERIFIED'}
                raise RequestServiceError('REQUEST_REPLAY_HELD')
            path = destination / ('dbvora-' + 'a'*32 + ('.zip' if codec == 'zip' else '.dbvz'))
            path.write_bytes(b'FAKE_ARCHIVE_FOR_ORCHESTRATION')
            published['file'] = path
            archive_sha['sha'] = hashlib.sha256(path.read_bytes()).hexdigest()
            if change_source:
                (snapshot.parent.parent / 'source' / 'generated.sqlite').write_bytes(b'mutated')
            return {'status': 'RECORDED_UNVERIFIED', 'artifact_name': path.name,
                    'independently_restored_content_verified': True,
                    'exactly_once_verified': False, 'ready_for_customer_data': False}
        def fake_inspect(ledger, directory, *, synthetic_only=False):
            path = published['file']
            valid = (hashlib.sha256(path.read_bytes()).hexdigest() == archive_sha['sha']
                     or ignore_corruption)
            return {'contract_version': 'dbvora.synthetic.request-reconcile.v1',
                    'inspection_mode': 'read_only_human_review_only',
                    'request_count': 1,
                    'counts': {'RECORDED_MATCH_REVIEW_REQUIRED': int(valid),
                               'RECORDED_NOT_VERIFIED': int(not valid),
                               'INTERRUPTED_REVIEW_REQUIRED': 0,
                               'DUPLICATE_ARTIFACT_REVIEW_REQUIRED': 0},
                    'unmatched_verified_archive_count': 0,
                    'may_resume_archive': False, 'exactly_once_verified': False,
                    'authenticity_verified': False, 'power_loss_verified': False,
                    'ready_for_customer_data': False}
        with patch.object(gate, 'create_snapshot', side_effect=fake_snapshot), \
             patch.object(gate, 'archive_once', side_effect=fake_archive), \
             patch.object(gate, 'inspect_and_reconcile', side_effect=fake_inspect):
            return gate._attempt(codec, self.base / ('real-'+codec))

    def test_zip_safe_control_flow_and_corruption_detection(self):
        result = self.simulate()
        self.assertEqual(result['checks'], 8)
        self.assertTrue(result['replay_held'])
        self.assertTrue(result['verified_then_corruption_held'])
        self.assertTrue(result['source_unchanged'])

    def test_zstd_safe_control_flow_and_corruption_detection(self):
        result = self.simulate(codec='zstd')
        self.assertTrue(result['verified_then_corruption_held'])

    def test_unblocked_replay_fails(self):
        with self.assertRaisesRegex(gate.GateError, 'REPLAY_WAS_NOT_BLOCKED'):
            self.simulate(fail_replay=True)

    def test_corrupted_artifact_must_not_remain_verified(self):
        with self.assertRaisesRegex(gate.GateError, 'AUDIT_COUNTS_OR_SAFETY_INVALID'):
            self.simulate(ignore_corruption=True)

    def test_mutated_source_is_rejected(self):
        with self.assertRaisesRegex(gate.GateError, 'ARCHIVE_OR_ORIGINAL_CHANGED'):
            self.simulate(change_source=True)

    def test_bad_recovery_claim_is_rejected(self):
        data = self.synthetic_report()
        data['power_loss_verified'] = True
        with self.assertRaisesRegex(gate.GateError, 'AUDIT_COUNTS_OR_SAFETY_INVALID'):
            gate._assert_report(data, expected_match=1, expected_missing=0)

    def test_duplicate_claim_not_accepted(self):
        data = self.synthetic_report()
        data['counts']['DUPLICATE_ARTIFACT_REVIEW_REQUIRED'] = 1
        with self.assertRaisesRegex(gate.GateError, 'AUDIT_COUNTS_OR_SAFETY_INVALID'):
            gate._assert_report(data, expected_match=1, expected_missing=0)

    def test_bad_record_state_not_accepted(self):
        data = self.synthetic_report()
        data['counts']['RECORDED_MATCH_REVIEW_REQUIRED'] = 0
        with self.assertRaises(gate.GateError):
            gate._assert_report(data, expected_match=1, expected_missing=0)

    def test_no_customer_data_claim_in_positive_summary(self):
        data = self.synthetic_report()
        self.assertNotIn('ready_for_customer_data', render(data).decode())

    def test_run_zip_only_when_codec_unavailable(self):
        with patch.object(gate, '_attempt', return_value={'checks': 8,
                'verified_then_corruption_held': True}), \
             patch.object(gate.shutil, 'which', return_value=None):
            result = gate.run()
        self.assertEqual(result['checks'], 8)
        self.assertEqual(result['optional_zstd'], 'skipped_no_local_codec')
        self.assertFalse(result['customer_ready'])

    def test_run_with_zstd_checks_both_backends(self):
        with patch.object(gate, '_attempt', return_value={'checks': 8,
                'verified_then_corruption_held': True}) as attempt, \
             patch.object(gate.shutil, 'which', return_value='/usr/bin/zstd'):
            result = gate.run()
        self.assertEqual(result['checks'], 16)
        self.assertEqual(result['optional_zstd'], 'passed')
        self.assertEqual(attempt.call_count, 2)

    def test_positive_summary_status_must_fail_when_fake_backend_breaks(self):
        with patch.object(gate, 'run', side_effect=gate.GateError('AUDIT_COUNTS_OR_SAFETY_INVALID')):
            output = io.StringIO()
            with redirect_stdout(output):
                code = gate.main()
        self.assertEqual(code, 1)
        self.assertIn('FAIL_CLOSED', output.getvalue())

    def test_gate_does_not_leak_private_path_on_failure(self):
        secret = '/private/customer/password.sqlite'
        with patch.object(gate, 'run', side_effect=OSError(secret)):
            out = io.StringIO()
            with redirect_stdout(out):
                code = gate.main()
        self.assertEqual(code, 1)
        self.assertNotIn(secret, out.getvalue())
        self.assertIn('GATE_FAILED', out.getvalue())

    def test_unexpected_failure_safe_code(self):
        with patch.object(gate, 'run', side_effect=RuntimeError('database credentials')):
            out = io.StringIO()
            with redirect_stdout(out):
                code = gate.main()
        self.assertEqual(code, 1)
        self.assertIn('UNEXPECTED_GATE_FAILURE', out.getvalue())
        self.assertNotIn('credentials', out.getvalue())

    def test_valid_report_contract(self):
        data = self.synthetic_report()
        gate._assert_report(data, expected_match=1, expected_missing=0)

    @staticmethod
    def synthetic_report():
        return {'inspection_mode': 'read_only_human_review_only', 'counts': {
                    'RECORDED_MATCH_REVIEW_REQUIRED': 1,
                    'RECORDED_NOT_VERIFIED': 0,
                    'INTERRUPTED_REVIEW_REQUIRED': 0,
                    'DUPLICATE_ARTIFACT_REVIEW_REQUIRED': 0},
                'may_resume_archive': False, 'ready_for_customer_data': False,
                'exactly_once_verified': False, 'power_loss_verified': False,
                'contract_version': 'dbvora.synthetic.request-reconcile.v1',
                'request_count': 1, 'unmatched_verified_archive_count': 0,
                'authenticity_verified': False}

if __name__ == '__main__':
    unittest.main()
