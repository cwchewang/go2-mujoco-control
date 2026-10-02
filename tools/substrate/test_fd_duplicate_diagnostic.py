import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.substrate import fd_duplicate_diagnostic as d


class FDDuplicateDiagnosticTest(unittest.TestCase):
    def test_derived_private_bounds(self):
        self.assertEqual(d.derive_bounds(), {
            'old_fd_calls': 37, 'fixed_fd_calls': 36,
            'old_fd_upper': 1801, 'fixed_fd_upper': 1752,
            'rollout_steps': 700, 'one_old_call': 2501,
            'one_fixed_call': 2452, 'eight_call_total': 19812,
            'eight_call_reservation': 32768})

    def test_protocol_matches_the_private_bound_and_no_canonical_steps(self):
        protocol=json.loads(d.PROTOCOL.read_text())
        self.assertEqual(protocol['optimizer_calls_max'],8)
        self.assertEqual(protocol['private_total_upper_bound'],19812)
        self.assertEqual(protocol['private_total_reserved_upper_bound'],32768)
        self.assertEqual(protocol['canonical_integration_steps'],0)
        self.assertEqual(protocol['anchors'],[0,10])
        self.assertEqual(protocol['variants'],['original','fixed'])
        self.assertEqual(protocol['workers'],4)
        d.validate_protocol(protocol)
        protocol['private_total_upper_bound']=999
        with self.assertRaisesRegex(ValueError,'protocol/source'):
            d.validate_protocol(protocol)

    def test_trial_matrix_is_exactly_eight_fresh_calls(self):
        plan=d.trial_plan()
        self.assertEqual(len(plan),8)
        self.assertEqual(plan[0],{'tick':0,'repeat':1,'variant':'original'})
        self.assertEqual(plan[-1],{'tick':10,'repeat':2,'variant':'fixed'})

    def test_duplicate_anchor_is_rejected(self):
        row={'tick':0,'controller_update':True,'failure':None,'warning_count':0,
             'terminal_reason':None,'sim_time_s':0.0,'qpos':[0.0]*19,'qvel':[0.0]*18,
             'command':[0.0]*3}
        with self.assertRaisesRegex(ValueError,'duplicate raw planner anchor'):
            d.anchors_from_raw_rows([row,row])

    def test_missing_anchor_is_rejected(self):
        row={'tick':0,'controller_update':True,'failure':None,'warning_count':0,
             'terminal_reason':None,'sim_time_s':0.0,'qpos':[0.0]*19,'qvel':[0.0]*18,
             'command':[0.0]*3}
        with self.assertRaisesRegex(ValueError,'tick 0/10'):
            d.anchors_from_raw_rows([row])

    def test_t34_and_budget_acceptance_for_both_variants(self):
        for variant,count,upper in (('original',37,1801),('fixed',36,1752)):
            knots=([*range(35),34,35] if variant=='original' else list(range(36)))
            events=[{'t':t,'worker':i%4,'start_ns':i*100+1,'end_ns':i*100+50}
                    for i,t in enumerate(knots)]
            if variant=='original':
                events[-2]['start_ns']=3420
                events[-2]['end_ns']=3460
            trace={'events':events,'index_count':count,'jacobian_t34_fnv1a64':'a'*16}
            anchor={'tick':0,'time_s':0.0,'command':[0.0]*3,'qpos':[0.0]*19,'qvel':[0.0]*18}
            states=[{'qpos':[0.0]*19,'qvel':[0.0]*18}]+[{} for _ in range(36)]
            preds=[{'policy_id':1,'candidate_id':2,'anchor_time_s':0.0,'states':states}]
            response={'ok':True,'replanned':True,'current_rollout_valid':True,
                'diagnostic':{'policy_id':1,'fd_call_count':count,
                    'fd_step_upper_bound_count':upper,'rollout_mj_step_count':700,
                    'private_step_upper_bound_reserved':4096,'private_step_limit':614400},
                'q_des':[0.0]*12,'cost':1.0}
            value=d.validate_response(variant,response,trace,preds,0,anchor)
            self.assertEqual(value['fd_calls'],count)
            self.assertEqual(value['private_call_upper_bound'],d.OLD_PRIVATE if variant=='original' else d.FIXED_PRIVATE)

    def test_candidate_anchor_mismatch_fails_closed(self):
        anchor={'tick':10,'time_s':0.02,'command':[0.0]*3,'qpos':[0.0]*19,'qvel':[1.0]*18}
        states=[{'qpos':[0.0]*19,'qvel':[0.0]*18}]+[{} for _ in range(36)]
        prediction={'policy_id':1,'candidate_id':0,'anchor_time_s':0.01,'states':states}
        response={'ok':True,'replanned':True,'current_rollout_valid':True,
                  'diagnostic':{'policy_id':1,'fd_call_count':36,
                      'fd_step_upper_bound_count':1752,'rollout_mj_step_count':700,
                      'private_step_upper_bound_reserved':4096,'private_step_limit':614400},
                  'cost':1.0,'q_des':[0.0]*12}
        events=[{'t':t,'worker':t%4,'start_ns':t*100+1,'end_ns':t*100+50}
                for t in range(36)]
        trace={'events':events,'index_count':36,'jacobian_t34_fnv1a64':'a'*16}
        with self.assertRaisesRegex(ValueError,'candidate trace mismatch'):
            d.validate_response('fixed',response,trace,[prediction],0,anchor)
        prediction['anchor_time_s']=anchor['time_s']
        with self.assertRaisesRegex(ValueError,'candidate initial state'):
            d.validate_response('fixed',response,trace,[prediction],0,anchor)

    def test_generator_preserves_old_schedule_and_traces_both_variants(self):
        source=d.ROOT/'.substrate/mjpc/mjpc/planners/model_derivatives.cc'
        script=d.ROOT/'tools/substrate/native/patch_mjpc_model_derivatives_diagnostic.py'
        with tempfile.TemporaryDirectory() as tmp:
            original=Path(tmp)/'original.cc'; fixed=Path(tmp)/'fixed.cc'
            subprocess.run([sys.executable,str(script),str(source),str(original),str(fixed)],
                           check=True,capture_output=True,text=True)
            old=original.read_text(); new=fixed.read_text()
        self.assertIn('legacy_indices.push_back(t)',old)
        self.assertIn('ModelDerivativeEvaluateIndices(T, skip)',new)
        for rendered in (old,new):
            self.assertIn('pool.WaitCount(count_before + evaluate_.size())',rendered)
            self.assertIn('jacobian_t34_fnv1a64',rendered)
            self.assertIn('fd_events[slot] = {t, worker, start_ns, FDTraceNowNs()}',rendered)

    def test_authorization_negative_case_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'explicit future user authorization'):
            d.validate_authorization({},'head','manifest')


if __name__=='__main__': unittest.main()
