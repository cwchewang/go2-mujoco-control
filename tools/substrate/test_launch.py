"""No dynamics integration. Synthetic plant exercises the actual episode loop."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

from .contracts import MOTOR_JOINTS, TorqueCommand, Proprioception
from .episode import episode, command_at
from .analyze_capture import analyze
from .integrity import strict_json
from .launch import PROTOCOL, validate_review, validate_authorization, wall_deadline, capture


class FakePlant:
    names = MOTOR_JOINTS
    qadr = list(range(7, 19))
    vadr = list(range(6, 18))
    lower, upper = np.full(12, -40.), np.full(12, 40.)

    def __init__(self, fault=None):
        self.fault = fault
        self.reset()

    def reset(self):
        self.steps = 0
        self.applied = []

    def snapshot(self, tick):
        qpos = np.zeros(19)
        qpos[:4] = [self.steps * .002 * .15, 0., .27, 1.]
        qpos[7:] = self.steps * .0001
        qvel = np.zeros(18)
        qvel[0] = .15
        row = dict(tick=tick, sim_time_s=self.steps * .002, qpos=qpos.tolist(), qvel=qvel.tolist(), initial_y=0., supports=["FR", "FL"], forbidden_contacts=[], warning_count=0)
        if self.fault:
            self.fault(row)
        return row

    def observe(self):
        row = self.snapshot(self.steps)
        return Proprioception(self.names, np.array(row["qpos"])[self.qadr], np.array(row["qvel"])[self.vadr], row["qpos"][3:7], row["qvel"][3:6])

    def step(self, ctrl):
        self.applied.append(ctrl.copy())
        self.steps += 1


class FakePolicy:
    def reset(self):
        self.calls = []

    def act(self, obs, command):
        self.calls.append(command)
        return TorqueCommand(MOTOR_JOINTS, np.zeros(12), np.ones(12), np.zeros(12), np.ones(12), np.zeros(12))


class LaunchTests(unittest.TestCase):
    def setUp(self):
        self.protocol = strict_json(PROTOCOL.read_text())
        self.short = copy.deepcopy(self.protocol)
        self.short.update(horizon_ticks=30, measurement_start_tick=10)
        self.short["thresholds"]["progress_min_m"] = .001
        self.layout = dict(names=MOTOR_JOINTS, qadr=list(range(7,19)), vadr=list(range(6,18)))

    def trace(self, protocol=None, fault=None, **kwargs):
        rows, consumed = [], []
        plant, policy = FakePlant(fault), FakePolicy()
        result = episode(plant, policy, protocol or self.short, rows.append, lambda: consumed.append(True), **kwargs)
        return rows, consumed, result, plant, policy

    def analyze(self, rows, protocol=None):
        return analyze(rows, protocol or self.short, FakePlant.lower, FakePlant.upper, self.layout)

    def test_entire_frozen_horizon_synthetic(self):
        rows, consumed, result, plant, policy = self.trace(self.protocol)
        self.assertEqual((plant.steps, len(rows), len(policy.calls), len(consumed)), (5000, 5001, 500, 1))
        self.assertEqual(self.analyze(rows, self.protocol)["verdict"], "PASS")

    def test_pd_recomputed_between_policy_updates(self):
        rows, _, _, plant, policy = self.trace()
        self.assertEqual(len(policy.calls), 3)
        self.assertNotEqual(rows[0]["action"]["ctrl"], rows[1]["action"]["ctrl"])
        self.assertEqual(rows[0]["target"], rows[9]["target"])
        self.assertEqual(self.analyze(rows)["verdict"], "PASS")

    def test_command_boundaries(self):
        self.assertEqual([command_at(self.protocol,t)[0] for t in (0,499,500,750,1000,4999)], [0,0,0,.075,.15,.15])

    def test_posture_stops_before_next_step(self):
        def fall(row):
            if row["tick"] == 7:
                row["qpos"][2] = .1
        rows, consumed, _, plant, _ = self.trace(fault=fall)
        self.assertEqual((plant.steps,len(rows),len(consumed)),(7,8,1))
        self.assertEqual(self.analyze(rows)["first_failure"], {"tick":7,"reason":"posture"})

    def test_initial_failure_never_consumes_attempt(self):
        rows, consumed, _, plant, _ = self.trace(fault=lambda row: row.update(warning_count=1))
        self.assertEqual((plant.steps,consumed), (0,[]))
        self.assertEqual(self.analyze(rows)["verdict"], "FAIL")

    def test_nonfoot_contact_stops(self):
        def touch(row):
            if row["tick"] == 3:
                row["forbidden_contacts"] = [[0,5]]
        rows, _, _, plant, _ = self.trace(fault=touch)
        self.assertEqual(plant.steps,3)
        self.assertEqual(self.analyze(rows)["first_failure"]["reason"], "nonfoot_contact")

    def test_clock_drift_rejected(self):
        with self.assertRaisesRegex(ValueError,"simulation time"):
            self.trace(fault=lambda row: row.update(sim_time_s=row["sim_time_s"]+.001))

    def test_wall_timeout_stops(self):
        counter=iter(range(1000))
        protocol=copy.deepcopy(self.short)
        protocol["wall_timeout_s"]=5
        rows, _, _, plant, _ = self.trace(protocol, monotonic=lambda: next(counter))
        self.assertLess(plant.steps,30)
        self.assertEqual(self.analyze(rows,protocol)["first_failure"]["reason"], "wall_timeout")

    def test_analyzer_rejects_truncation_duplicates_and_label_edits(self):
        rows=self.trace()[0]
        cases=[rows[:-1],rows[:5]+rows[4:]]
        edited=copy.deepcopy(rows)
        edited[5]["failure"]="posture"
        cases.append(edited)
        for bad in cases:
            with self.subTest(length=len(bad)), self.assertRaises(ValueError):
                self.analyze(bad)

    def test_analyzer_detects_stale_pd_even_when_torque_sum_valid(self):
        rows=self.trace()[0]
        rows[1]["action"]=copy.deepcopy(rows[0]["action"])
        with self.assertRaisesRegex(ValueError,"PD or joint"):
            self.analyze(rows)

    def test_analyzer_rejects_out_of_cadence_policy_update(self):
        rows=self.trace()[0]
        rows[1]["policy_wall_s"]=.001
        with self.assertRaisesRegex(ValueError,"outside control"):
            self.analyze(rows)

    def test_analyzer_does_not_promote_endpoint_metric_failure(self):
        rows=self.trace()[0]
        p=copy.deepcopy(self.short)
        p["thresholds"]["progress_min_m"]=10
        self.assertEqual(self.analyze(rows,p)["verdict"],"FAIL")

    def test_review_is_exact_and_independent(self):
        review=dict(head="a"*40,science=dict(verdict="APPROVED",reviewer="science-reviewer",evidence="review transcript"),execution=dict(verdict="APPROVED",reviewer="execution-reviewer",evidence="review transcript"))
        validate_review(review,"a"*40)
        with self.assertRaises(ValueError): validate_review(review,"b"*40)
        review["execution"]["reviewer"]="science-reviewer"
        with self.assertRaises(ValueError): validate_review(review,"a"*40)

    def test_preparation_is_not_start_authorization(self):
        prepared=dict(head="a"*40,protocol_sha256="b"*64,prepared_manifest_sha256="c"*64)
        for value in ({},dict(action="PREPARE"),dict(action="START_FORMAL_CAPTURE",**prepared,max_attempts=True,authorized_by="user",user_instruction="start")):
            with self.assertRaises(ValueError): validate_authorization(value,prepared)
        validate_authorization(dict(action="START_FORMAL_CAPTURE",**prepared,max_attempts=3,authorized_by="user",user_instruction="start frozen experiment"),prepared)

    def test_capture_rejects_unapproved_input_before_plant(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            prepared=dict(readiness="READY_AWAITING_START",head="a"*40,source_files={},protocol_sha256=__import__("hashlib").sha256(PROTOCOL.read_bytes()).hexdigest())
            (root/"manifest.json").write_text("{}")
            (root/"auth.json").write_text("{}")
            with patch("tools.substrate.launch.LOCK_PATH",root/"lock"),patch("tools.substrate.launch.verify_bundle",return_value=prepared),patch("tools.substrate.launch.current_identity",return_value=("a"*40,{})),patch("tools.substrate.launch.MujocoPlant") as plant:
                with self.assertRaises(ValueError): capture(root,root/"auth.json",root/"capture")
                plant.assert_not_called()
                self.assertFalse((root/"capture").exists())

    def test_wall_alarm_interrupts_stalled_backend(self):
        import time
        with self.assertRaises(TimeoutError):
            with wall_deadline(.01): time.sleep(.1)

    def test_independent_watchdog_kills_signal_ignoring_owner(self):
        code = "from tools.substrate.launch import wall_deadline; import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); context=wall_deadline(.01); context.__enter__(); signal.signal(signal.SIGALRM,signal.SIG_IGN); time.sleep(10)"
        result = subprocess.run([sys.executable,"-c",code],capture_output=True,timeout=6)
        self.assertEqual(result.returncode,-9)

    def test_repeatability_is_not_inferred_from_three_metric_passes(self):
        rows=self.trace()[0]
        result=analyze(rows,self.short,FakePlant.lower,FakePlant.upper,self.layout,"0"*64)
        self.assertEqual(result["verdict"],"FAIL")
        self.assertFalse(result["repeatability_matches"])

    def test_zero_step_guard_covers_all_integrators_without_calling_them(self):
        import types
        from .launch import zero_step_guard
        fake=types.SimpleNamespace(mj_step=lambda: None,mj_step1=lambda:None,mj_step2=lambda:None)
        original=fake.mj_step
        with patch.dict(sys.modules,{"mujoco":fake}):
            with zero_step_guard():
                for name in ("mj_step","mj_step1","mj_step2"):
                    with self.assertRaisesRegex(RuntimeError,"forbids"):
                        getattr(fake,name)()
            self.assertIs(fake.mj_step,original)

    def campaign(self, fault=None):
        """Real launcher/evidence/ledger, synthetic plant and short protocol."""
        from contextlib import ExitStack
        from . import launch
        from .integrity import EvidenceRun, write_new, digest, verify_bundle, verify_manifest
        from .verify_capture import verify_capture
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        protocol_path = root / "protocol.json"
        write_new(protocol_path, self.short)
        checkpoint = root / "policy.pt"
        checkpoint.write_bytes(b"fixture")
        review = dict(head="a"*40, science=dict(verdict="APPROVED", reviewer="one", evidence="fixture"), execution=dict(verdict="APPROVED", reviewer="two", evidence="fixture"))
        plant = FakePlant(fault)
        plant.model = None
        prepared_path = root / "prepared"
        with EvidenceRun(prepared_path) as run:
            run.result.update(status="ENGINEERING_ADMITTED", readiness="READY_AWAITING_START", head="a"*40, source_files={}, protocol_sha256=digest(protocol_path), checkpoint_sha256=digest(checkpoint), review=review, model={}, physical_sha256="fixture", layout=self.layout, lower=plant.lower.tolist(), upper=plant.upper.tolist())
            write_new(run.path / "protocol.json", self.short)
            write_new(run.path / "initial-state.json", plant.snapshot(0))
        auth = dict(action="START_FORMAL_CAPTURE",head="a"*40,protocol_sha256=digest(protocol_path),prepared_manifest_sha256=digest(prepared_path/"manifest.json"),max_attempts=3,authorized_by="user",user_instruction="synthetic test fixture only")
        write_new(root / "auth.json", auth)
        with ExitStack() as stack:
            patches = dict(ROOT=root, PROTOCOL=protocol_path, CHECKPOINT=checkpoint, LOCK_PATH=root/"lock")
            for name,value in patches.items(): stack.enter_context(patch.object(launch,name,value))
            for name,value in dict(current_identity=("a"*40,{}),verify_environment={},setup_runtime=None,dependency_manifest={},physical_fingerprint="fixture").items(): stack.enter_context(patch.object(launch,name,return_value=value))
            stack.enter_context(patch.object(launch,"preflight",side_effect=lambda lock,head,review,report,fresh: write_new(report,{"pass":True,"git":{"head":head}})))
            stack.enter_context(patch.object(launch,"MujocoPlant",return_value=plant))
            stack.enter_context(patch.object(launch,"FrozenPolicy",return_value=FakePolicy()))
            result = capture(prepared_path,root/"auth.json",root/"capture")
            verified = verify_capture(root/"capture",prepared_path)
            with self.assertRaisesRegex(ValueError,"already claimed"):
                capture(prepared_path,root/"auth.json",root/"replacement")
            self.assertFalse((root/"replacement").exists())
        return result, verified, verify_manifest(root/"capture"), root

    def test_campaign_three_passes_and_independent_reanalysis(self):
        result, verified, record, root = self.campaign()
        self.assertEqual((result["capability_status"],record["live_runs"]),("PASS",3))
        self.assertEqual([a["status"] for a in verified["attempts"]],["PASS"]*3)

    def test_campaign_stops_after_first_failure_without_replacement(self):
        def fall(row):
            if row["tick"] == 7: row["qpos"][2]=.1
        result, verified, record, root = self.campaign(fall)
        self.assertEqual(record["live_runs"],1)
        self.assertEqual([a["status"] for a in verified["attempts"]],["FAIL","NOT_RUN","NOT_RUN"])
        self.assertFalse((root/"capture/attempt_02.jsonl").exists())

    def test_bad_quaternion_terminal_is_preserved_and_classified(self):
        def bad(row):
            if row["tick"] == 30: row["qpos"][3] = 1.001
        rows, _, _, _, _ = self.trace(fault=bad)
        self.assertEqual(self.analyze(rows)["first_failure"],{"tick":30,"reason":"orientation"})

    def test_outer_timeout_reaps_term_ignoring_test_group(self):
        from .integrity import run_logged
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            child=root/"child.py"
            child.write_text("import os,signal,time\nfrom pathlib import Path\nsignal.signal(signal.SIGTERM,signal.SIG_IGN)\nPath("+repr(str(root/"pid"))+").write_text(str(os.getpid()))\ntime.sleep(30)\n")
            wrapper=root/"wrapper.py"
            wrapper.write_text("import signal,sys\nfrom pathlib import Path\nfrom tools.research.preflight import command\ndef stop(*args): raise RuntimeError('fixture')\nsignal.signal(signal.SIGTERM,stop)\ncommand([sys.executable,"+repr(str(child))+"],Path.cwd())\n")
            # -c imports from checkout, while the child's executable fixture is isolated.
            code="exec("+repr(wrapper.read_text())+")"
            with self.assertRaises(subprocess.TimeoutExpired):
                run_logged([sys.executable,"-c",code],root,"timeout",timeout=.5,termination_grace=2)
            pid=int((root/"pid").read_text())
            self.assertFalse(Path(f"/proc/{pid}").exists())

    def test_formal_verifier_requires_authorization_and_correct_consumption(self):
        from .verify_capture import verify_capture
        from .integrity import digest
        _, _, _, root = self.campaign()
        directory = root / "capture"
        record_path = directory / "admission.json"
        original = record_path.read_text()
        data = json.loads(original)
        data["live_runs"] = 0
        record_path.write_text(json.dumps(data))
        def reseal_fixture():
            (directory/"manifest.json").write_text(json.dumps({p.relative_to(directory).as_posix():digest(p) for p in directory.rglob("*") if p.is_file() and p.name!="manifest.json"}))
        reseal_fixture()
        with self.assertRaisesRegex(ValueError,"count mismatch"):
            verify_capture(directory,root/"prepared")
        record_path.write_text(original)
        (directory/"authorization.json").write_text("{}")
        reseal_fixture()
        with self.assertRaisesRegex(ValueError,"authorization"):
            verify_capture(directory,root/"prepared")


if __name__ == "__main__":
    unittest.main()
