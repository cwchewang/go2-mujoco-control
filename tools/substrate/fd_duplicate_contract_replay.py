"""Replay sealed native logs through the live consumer; no controller or physics launch."""
import argparse
import ast
from pathlib import Path
from . import fd_duplicate_diagnostic as d

LEGACY_HEAD='973db057ed4957f6606c532645887593aaa7a23c'

def legacy_failure(directory,anchor):
    source=d.git('show',LEGACY_HEAD+':tools/substrate/fd_duplicate_diagnostic.py')
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='validate_response')
    namespace=dict(vars(d))
    exec(compile(ast.Module(body=[node],type_ignores=[]),'sealed-legacy-consumer','exec'),namespace)
    rows=[d.strict_json(x) for x in (Path(directory)/'native.jsonl').read_text().splitlines()]
    trace=d.strict_json((Path(directory)/'fd-trace.jsonl').read_text())
    predictions=[d.strict_json((Path(directory)/'predictions.jsonl').read_text())]
    try: namespace['validate_response']('original',rows[1]['response'],trace,predictions,0,anchor)
    except ValueError as exc:
        if str(exc)!='candidate horizon/state dimensions mismatch': raise
        return str(exc)
    raise AssertionError('old 37-state consumer unexpectedly accepted real 36-state output')

def replay(source_run,prepared_path,output):
    source_run=Path(source_run).resolve(strict=True); prepared_path=Path(prepared_path).resolve(strict=True)
    d.validate_run_record_paths(prepared_path,output=output)
    if Path(output).resolve().is_relative_to(source_run):
        raise ValueError('replay output must be outside source run')
    with d.zero_step_guard():
        source_admission=d.verify_manifest(source_run); d.verify_manifest(prepared_path)
        protocol=d.strict_json((prepared_path/'protocol.json').read_text()); d.validate_protocol(protocol)
        inputs=d.strict_json((prepared_path/'inputs.json').read_text())
        ids=d.strict_json((prepared_path/'binary-identities.json').read_text())
        anchors={a['tick']:a for a in inputs['anchors']}
        plan=[t for t in d.trial_plan() if (source_run/f"tick{t['tick']}_{t['variant']}_repeat{t['repeat']}").is_dir()]
        if not plan: raise ValueError('no real trial logs to replay')
        producer=(d.ROOT/'tools/substrate/native/diagnostic.h').read_text()
        if ('for (int t=0; t<best.horizon; ++t)' not in producer or
            'best.horizon != 36 || best.dim_state != 37' not in producer or
            'best.actions.data()+12*t' not in producer):
            raise ValueError('native producer source contract changed; re-audit required')
        legacy=legacy_failure(source_run/'tick0_original_repeat1',anchors[0])
        completed,records,stop=d.collect_trials(plan,anchors,ids,source_run,d.parse_trial_logs)
        with d.EvidenceRun(Path(output),{'operation':'zero_physics_real_native_response_replay'}) as record:
            record.result.update(scope='offline_fd_contract_replay',canonical_integration_steps=0,
                source_manifest_sha256=d.digest(source_run/'manifest.json'),head=d.git('rev-parse','HEAD'))
            result=d.make_result({'head':d.git('rev-parse','HEAD')},inputs,ids,plan,completed,records,stop,prepared_path,offline=True)
            result.update(source_run=str(source_run),source_manifest_sha256=d.digest(source_run/'manifest.json'),
                source_head=source_admission['head'],source_original_status=source_admission['status'],
                source_original_stop_reason=source_admission.get('stop_reason'),
                historical_optimizer_calls_attempted=sum(r['optimizer_call_attempted'] for r in records),
                source_original_accepted_trials=source_admission.get('optimizer_calls_completed'),
                offline_replay_accepted_trials=len(completed))
            d.record_result(record,result,offline=True)
            trial=source_run/'tick0_original_repeat1'
            rows=[d.strict_json(x) for x in (trial/'native.jsonl').read_text().splitlines()]
            d.write_new(record.path/'contract-verification.json',{
                'legacy_head':LEGACY_HEAD,'legacy_rejection':legacy,
                'producer_sources':{f:d.digest(d.ROOT/f) for f in (
                    'tools/substrate/native/controller.cc','tools/substrate/native/diagnostic.h',
                    'tools/substrate/native/patch_mjpc_model_derivatives_diagnostic.py')},
                'source_manifest_sha256':d.digest(source_run/'manifest.json'),
                'generated_sources':{v:ids[v]['generated_source_sha256'] for v in ids},
                'producer_count_evidence':'for (int t=0; t<best.horizon; ++t); best.horizon=36; dim_state=37; action stride=12',
                'source_files':{f:d.digest(trial/f) for f in ('native.jsonl','native.stderr.log','fd-trace.jsonl','predictions.jsonl')},
                'native_startup_contract':d.candidate_contract(rows[0]['ready']),
                'new_optimizer_calls':0,'canonical_integration_steps':0,
                'audited_field_groups':{
                    'startup':'controller.cc: protocol3, nq19/nv18/nu12, worker4, horizon36/dt.01; source PD/gait/warning semantics',
                    'request':'controller.cc main: step replan time vx/vy/wz qpos19 qvel18; exact logged packet equality',
                    'response':'controller.cc Step: ok/replanned/fresh candidate, cost, time/vx/wz, q_des12, private counters',
                    'trajectory':'diagnostic.h Record: horizon36 knots, internal state37=qpos19+qvel18, action12, times and contacts',
                    'candidate_identity':'diagnostic.h: policy1, BestRollout in 0..9, mode original/fixed and model id',
                    'budget':'Diagnostic Reserve and diagnostic_budget.cc wrappers: reservation4096, fd count/upper, rollout700',
                    'FD_trace':'generated model_derivatives: original37/fixed36 scheduled calls, knot34 duplication, workers/intervals/barrier hash',
                    'informational_only':'planning_compute_us/action_compute_us are recorded, not acceptance thresholds'},
                'minimum_differences':[
                    '36 trajectory knots vs 37 internal qpos+qvel components; original FD schedule separately has 37 calls',
                    'all state/action/time/contact fields and mode/model/accounting checked against the same startup contract',
                    'attempted trials and raw budget retained when a candidate is rejected',
                    'live and offline share parse_trial_logs, collect_trials, make_result and record_result'],
                'original_failure_preserved':True})
    return str(Path(output)/'RESULT.json')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run',type=Path,required=True)
    parser.add_argument('--prepared',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args(); print(replay(a.source_run,a.prepared,a.output))

if __name__=='__main__': main()
