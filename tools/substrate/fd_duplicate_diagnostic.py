"""Bounded fixed-input private MJPC FD comparison; never touches old evidence."""
from __future__ import annotations
import argparse, json, math, os, re, subprocess, sys
from pathlib import Path
from .guards import wall_deadline, zero_step_guard
from .integrity import EvidenceRun, digest, experiment_lock, strict_json, verify_manifest, write_new
from .native_transport import NativeTransport
from .readiness import validate_review

ROOT=Path(__file__).resolve().parents[2]
PROTOCOL=ROOT/'tools/substrate/protocols/mjpc_fd_duplicate_diagnostic_v1.json'
CAPTURE=ROOT/'_runs/mjpc_adaptation_diagnostic_execution_20261002/original_capture_20261002T164948Z'
BRANCH='research/mjpc-fd-duplicate-fix-20261003'
TASK=ROOT/'.substrate/mjpc/mjpc/tasks/quadruped/task_flat.xml'
CANON=ROOT/'unitree_robots/go2/phase2_flat.xml'
UPSTREAM='e00c47a5adb9856af2e0f24231bb3a60d5be23c4'
OLD_PRIVATE, FIXED_PRIVATE = 2501, 2452
OLD_FD, FIXED_FD = (37,1801), (36,1752)
ROLLOUT_STEPS, RESERVATION, LIMIT = 700,4096,614400
TOTAL_UPPER, TOTAL_RESERVED = 19812,32768

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,text=True,stderr=subprocess.PIPE).strip()

def root_identity():
    branch,head=git('branch','--show-current'),git('rev-parse','HEAD')
    if branch!=BRANCH or git('status','--porcelain'):
        raise ValueError('requires exact clean diagnostic branch checkout')
    return {'branch':branch,'head':head}

def model_identity():
    return {
        'source_task': {'path': str(TASK), 'sha256': digest(TASK)},
        'canonical_evaluation': {'path': str(CANON), 'sha256': digest(CANON)},
    }

def derive_bounds():
    legacy=[0]+list(range(1,35))+[34,35]
    fixed=list(dict.fromkeys(legacy))
    old_fd=(len(legacy)-1)*49+37
    new_fd=(len(fixed)-1)*49+37
    return {'old_fd_calls':len(legacy),'fixed_fd_calls':len(fixed),
            'old_fd_upper':old_fd,'fixed_fd_upper':new_fd,
            'rollout_steps':ROLLOUT_STEPS,
            'one_old_call':old_fd+ROLLOUT_STEPS,
            'one_fixed_call':new_fd+ROLLOUT_STEPS,
            'eight_call_total':4*(old_fd+ROLLOUT_STEPS)+4*(new_fd+ROLLOUT_STEPS),
            'eight_call_reservation':8*RESERVATION}

def validate_protocol(protocol):
    expected = {
        'schema': 1,
        'task_id': 'mjpc-fd-duplicate-causal-diagnostic-v1',
        'upstream_commit': UPSTREAM,
        'index_patch_sha256': '75e399969b94eb690b680cb83c8624d6b4b0067d159ef02e9611c5dfbed32b0d',
        'anchors': [0, 10],
        'repeats_per_variant_anchor': 2,
        'variants': ['original', 'fixed'],
        'workers': 4,
        'horizon_steps': 36,
        'derivative_skip': 0,
        'nominal_rollouts': 10,
        'planner_dt_s': 0.01,
        'seed': 'not_used_xfrc_std_zero',
        'cold_start': 'fresh controller and worker mjData per trial',
        'tick10_replay_limit': 'raw has qpos/qvel/command but not prior planner policy or worker state',
        'canonical_integration_steps': 0,
        'optimizer_calls_max': 8,
        'private_total_upper_bound': TOTAL_UPPER,
        'private_total_reserved_upper_bound': TOTAL_RESERVED,
        'private_limit': LIMIT,
        'wall_timeout_s': 300,
        'native_timeout_s': 30,
        'failure_policy': 'stop at first identity, warning, trace or budget failure; no retries',
        'scientific_gate': 'none; observations only',
    }
    if (not isinstance(protocol, dict) or set(protocol) != set(expected) or
        any(type(protocol.get(key)) is not type(value) or protocol[key] != value
            for key, value in expected.items()) or
        digest(ROOT/'tools/substrate/native/patches/mjpc-model-derivatives-e00c47a5.patch') !=
            expected['index_patch_sha256']):
        raise ValueError('diagnostic protocol/source does not match the reviewed fixed plan')

def trial_plan():
    return [{'tick':t,'repeat':n,'variant':v} for t in (0,10) for n in (1,2) for v in ('original','fixed')]

def anchors_from_raw_rows(source_rows):
    rows={}
    for row in source_rows:
        tick=row.get('tick')
        if type(tick) is int and tick in (0,10):
            if tick in rows: raise ValueError('duplicate raw planner anchor tick')
            rows[tick]=row
    if set(rows)!={0,10}: raise ValueError('sealed raw lacks tick 0/10')
    result=[]
    for tick in (0,10):
        r=rows[tick]; qpos=r.get('qpos'); qvel=r.get('qvel'); command=r.get('command')
        if (r.get('controller_update') is not True or r.get('failure') is not None or
            r.get('warning_count')!=0 or r.get('terminal_reason') is not None or
            not isinstance(qpos,list) or len(qpos)!=19 or not isinstance(qvel,list) or len(qvel)!=18 or
            not isinstance(command,list) or len(command)!=3 or
            any(type(x) not in (int,float) or not math.isfinite(x) for x in qpos+qvel+command) or
            not math.isclose(r.get('sim_time_s',-1),tick*.002,rel_tol=0,abs_tol=1e-9)):
            raise ValueError('invalid raw planner anchor')
        result.append({'tick':tick,'time_s':r['sim_time_s'],'command':command,'qpos':qpos,'qvel':qvel})
    return result

def anchors_from_raw(raw_path):
    return anchors_from_raw_rows([strict_json(line) for line in Path(raw_path).read_text().splitlines()])

def build_identity(binary,variant):
    binary=Path(binary).resolve(strict=True)
    if binary.name!=f'go2_mjpc_controller_fd_{variant}' or not os.access(binary,os.X_OK):
        raise ValueError('wrong or non-executable diagnostic binary')
    build=binary.parent; cache=build/'CMakeCache.txt'
    ninja=build/'build.ninja'; commands=build/'compile_commands.json'
    vals={}
    for line in cache.read_text().splitlines():
        m=re.match(r'([^:=]+):[^=]*=(.*)',line)
        if m: vals[m.group(1)]=m.group(2)
    if (vals.get('GO2_MJPC_BUILD_FD_DIAGNOSTIC')!='ON' or
        vals.get('CMAKE_BUILD_TYPE')!='Release' or
        Path(vals.get('MJPC_SOURCE_DIR','')).resolve()!=ROOT/'.substrate/mjpc' or
        vals.get('CMAKE_CXX_COMPILER')!='/usr/bin/c++' or
        vals.get('CMAKE_GENERATOR')!='Ninja' or
        vals.get('CMAKE_HOME_DIRECTORY')!=str(ROOT/'tools/substrate/native') or
        vals.get('FETCHCONTENT_FULLY_DISCONNECTED')!='ON' or
        not all(p.is_file() for p in (ninja,commands))):
        raise ValueError('unapproved binary build configuration')
    generated=build/'generated'/f'model_derivatives_fd_{variant}.cc'
    patch_script=ROOT/'tools/substrate/native/patch_mjpc_model_derivatives_diagnostic.py'
    if not generated.is_file(): raise ValueError('generated derivative source missing')
    return {'variant':variant,'path':str(binary),'binary_sha256':digest(binary),
            'generated_source_sha256':digest(generated),
            'diagnostic_patch_script_sha256':digest(patch_script),
            'index_patch_sha256':digest(ROOT/'tools/substrate/native/patches/mjpc-model-derivatives-e00c47a5.patch'),
            'index_patch_applier_sha256':digest(ROOT/'tools/substrate/native/patch_mjpc_model_derivatives.py'),
            'index_helper_header_sha256':digest(ROOT/'tools/substrate/native/model_derivative_indices.h'),
            'cache_sha256':digest(cache),'build_ninja_sha256':digest(ninja),
            'compile_commands_sha256':digest(commands),
            'mjpc_commit':git('-C',str(ROOT/'.substrate/mjpc'),'rev-parse','HEAD'),
            'mjpc_source_sha256':digest(ROOT/'.substrate/mjpc/mjpc/planners/model_derivatives.cc'),
            'workers':4}

def prepare(capture,original_binary,fixed_binary,output):
    with experiment_lock(),zero_step_guard():
        identity=root_identity()
        protocol=strict_json(PROTOCOL.read_text())
        validate_protocol(protocol)
        if derive_bounds()['eight_call_total']!=TOTAL_UPPER or derive_bounds()['eight_call_reservation']!=TOTAL_RESERVED:
            raise ValueError('private budget derivation mismatch')
        capture=Path(capture).resolve(strict=True)
        admission=verify_manifest(capture)
        manifest=strict_json((capture/'manifest.json').read_text())
        raw=capture/'raw.jsonl'
        if admission.get('task_id')!='mjpc-adaptation-original-3s-v1' or manifest.get('raw.jsonl')!=digest(raw):
            raise ValueError('input is not intact sealed original raw')
        anchors=anchors_from_raw(raw)
        models=model_identity()
        original=build_identity(original_binary,'original')
        fixed=build_identity(fixed_binary,'fixed')
        shared = ('cache_sha256','build_ninja_sha256','compile_commands_sha256',
                  'mjpc_commit','mjpc_source_sha256','diagnostic_patch_script_sha256',
                  'index_patch_sha256','index_patch_applier_sha256','index_helper_header_sha256')
        if (original['binary_sha256']==fixed['binary_sha256'] or
            Path(original['path']).parent != Path(fixed['path']).parent or
            any(original[key]!=fixed[key] for key in shared) or
            any(x['mjpc_commit']!=UPSTREAM for x in (original,fixed))):
            raise ValueError('paired binary or pinned source identity mismatch')
        with EvidenceRun(Path(output),{'operation':'fd_duplicate_diagnostic_prepare'}) as run:
            write_new(run.path/'protocol.json',protocol)
            write_new(run.path/'inputs.json',{'capture_path':str(capture),
                'capture_manifest_sha256':digest(capture/'manifest.json'),
                'raw_sha256':digest(raw),'anchors':anchors,'models':models,
                'internal_state_restore':'fresh controller/worker mjData per trial; A tick 10 private planner state is absent from raw',
                'seed':'not used; rollout xfrc_std=0'})
            write_new(run.path/'binary-identities.json',{'original':original,'fixed':fixed})
            run.result.update(status='ENGINEERING_ADMITTED',scope='private_fd_duplicate_prepare',
                task_id=protocol['task_id'],**identity,protocol_sha256=digest(PROTOCOL),
                optimizer_calls_max=8,private_total_upper_bound=TOTAL_UPPER,
                private_total_reserved_upper_bound=TOTAL_RESERVED,canonical_integration_steps=0)
    return str(output)

def validate_authorization(auth,head,prepared_manifest):
    expected={'action':'RUN_MJPC_FD_DUPLICATE_DIAGNOSTIC','head':head,
        'prepared_manifest_sha256':prepared_manifest,'max_optimizer_calls':8,
        'private_total_upper_bound':TOTAL_UPPER,
        'private_total_reserved_upper_bound':TOTAL_RESERVED}
    if not isinstance(auth,dict) or any(auth.get(k)!=v for k,v in expected.items()) or auth.get('authorized_by')!='user' or not str(auth.get('user_instruction','')).strip():
        raise ValueError('explicit future user authorization does not match prepared run')

def validate_response(variant,response,trace,predictions,stderr_bytes,anchor):
    fd_calls,fd_upper=(OLD_FD if variant=='original' else FIXED_FD)
    diag=response.get('diagnostic',{})
    if (response.get('ok') is not True or response.get('replanned') is not True or
        response.get('current_rollout_valid') is not True or diag.get('policy_id')!=1 or
        diag.get('fd_call_count')!=fd_calls or diag.get('fd_step_upper_bound_count')!=fd_upper or
        diag.get('rollout_mj_step_count')!=ROLLOUT_STEPS or
        diag.get('private_step_upper_bound_reserved')!=RESERVATION or
        diag.get('private_step_limit')!=LIMIT or stderr_bytes!=0):
        raise ValueError('native warning, candidate, identity or private budget mismatch')
    events=trace.get('events')
    t34=2 if variant=='original' else 1
    expected_knots=([*range(35),34,35] if variant=='original' else list(range(36)))
    if (trace.get('index_count')!=fd_calls or not isinstance(events,list) or len(events)!=fd_calls or
        [e.get('t') for e in events]!=expected_knots or
        sum(e.get('t')==34 for e in events)!=t34 or
        any(type(e.get('worker')) is not int or e['worker'] not in range(4) or
            type(e.get('start_ns')) is not int or type(e.get('end_ns')) is not int or
            e['start_ns']>=e['end_ns'] for e in events) or
        not re.fullmatch(r'[0-9a-f]{16}',trace.get('jacobian_t34_fnv1a64','')) or
        len(predictions)!=1 or predictions[0].get('policy_id')!=1 or
        type(predictions[0].get('candidate_id')) is not int or
        predictions[0]['candidate_id'] not in range(10) or
        not math.isclose(predictions[0].get('anchor_time_s',-1),anchor['time_s'],rel_tol=0,abs_tol=1e-12) or
        not math.isfinite(response.get('cost',float('nan'))) or
        not isinstance(response.get('q_des'),list) or len(response['q_des'])!=12 or
        any(type(x) not in (int,float) or not math.isfinite(x) for x in response['q_des'])):
        raise ValueError('FD worker/knot/Jacobian or candidate trace mismatch')
    states=predictions[0].get('states')
    if not isinstance(states,list) or len(states)!=37 or not isinstance(states[0],dict):
        raise ValueError('candidate horizon/state dimensions mismatch')
    first=states[0]
    if (not isinstance(first.get('qpos'),list) or len(first['qpos'])!=19 or
        not isinstance(first.get('qvel'),list) or len(first['qvel'])!=18 or
        any(type(x) not in (int,float) or not math.isfinite(x) for x in first['qpos']+first['qvel']) or
        any(not math.isclose(float(x),float(y),rel_tol=0,abs_tol=1e-12)
            for x,y in zip(first['qpos']+first['qvel'],anchor['qpos']+anchor['qvel']))):
        raise ValueError('candidate initial state does not match fixed input anchor')
    events34=[e for e in events if e['t']==34]
    overlap=len(events34)==2 and events34[0]['start_ns']<events34[1]['end_ns'] and events34[1]['start_ns']<events34[0]['end_ns']
    return {'fd_calls':fd_calls,'fd_step_upper_bound':fd_upper,'rollout_steps':ROLLOUT_STEPS,
        'private_call_upper_bound':OLD_PRIVATE if variant=='original' else FIXED_PRIVATE,
        'jacobian_t34_fnv1a64':trace['jacobian_t34_fnv1a64'],
        't34_overlap':overlap,'t34_workers':[e['worker'] for e in events34],
        'candidate_id':predictions[0]['candidate_id'],'cost':response.get('cost'),
        'q_des':response.get('q_des')}

def _packet(anchor):
    values=[anchor['time_s'],*anchor['command'],*anchor['qpos'],*anchor['qvel']]
    return 'step 1 '+' '.join(format(float(x),'.17g') for x in values)

def run_trial(trial,anchor,binaries,identities,directory):
    directory.mkdir(parents=True,exist_ok=False)
    trace=directory/'fd-trace.jsonl'; native_log=directory/'native.jsonl'
    stderr_log=directory/'native.stderr.log'; predictions=directory/'predictions.jsonl'
    argv=[str(binaries[trial['variant']]),str(TASK),trial['variant'],str(CANON),str(predictions)]
    def popen(args,**kwargs):
        env=os.environ.copy(); env['GO2_MJPC_FD_TRACE_PATH']=str(trace)
        return subprocess.Popen(args,env=env,**kwargs)
    transport=NativeTransport(argv,popen=popen,stderr_log_path=stderr_log)
    packet=_packet(anchor)
    try:
        ready=transport.read_json(10)
        with native_log.open('x') as f:
            f.write(json.dumps({'ready':ready},sort_keys=True)+'\n'); f.flush(); os.fsync(f.fileno())
        if (ready.get('ready') is not True or ready.get('worker_count')!=4 or
            ready.get('planner')!='MJPC iLQG' or ready.get('horizon_steps')!=36 or
            not math.isclose(ready.get('planner_dt',-1),.01,rel_tol=0,abs_tol=1e-12)):
            raise ValueError('native startup configuration mismatch')
        response=transport.request(packet,30)
        with native_log.open('a') as f:
            f.write(json.dumps({'request':packet,'response':response},sort_keys=True,allow_nan=False)+'\n')
            f.flush(); os.fsync(f.fileno())
    finally:
        transport.close()
    stderr=transport.diagnostics()
    if stderr['stderr_read_error'] or stderr['stderr_bytes']:
        raise ValueError('warning or stderr drain failure')
    trace_rows=[strict_json(x) for x in trace.read_text().splitlines()]
    candidates=[strict_json(x) for x in predictions.read_text().splitlines()]
    observation=validate_response(trial['variant'],response,trace_rows[0] if len(trace_rows)==1 else {},
                                  candidates,stderr['stderr_bytes'],anchor)
    return {**trial,'binary_identity':identities[trial['variant']],
        'logs':{'native':'native.jsonl','stderr':'native.stderr.log',
                'fd_worker_knots':'fd-trace.jsonl','candidate':'predictions.jsonl'},
        'observation':observation}

def repeat_summary(completed):
    keyed={(r['tick'],r['variant'],r['repeat']):r for r in completed}
    out=[]
    for tick in (0,10):
        for variant in ('original','fixed'):
            a=keyed.get((tick,variant,1)); b=keyed.get((tick,variant,2))
            if a and b:
                x,y=a['observation'],b['observation']
                out.append({'tick':tick,'variant':variant,
                    'exact_jacobian_hash_match':x['jacobian_t34_fnv1a64']==y['jacobian_t34_fnv1a64'],
                    'exact_cost_match':x['cost']==y['cost'],'exact_q_des_match':x['q_des']==y['q_des'],
                    't34_overlap':[x['t34_overlap'],y['t34_overlap']]})
    return out

def run(prepared_path,review_path,authorization_path,output):
    with experiment_lock():
        prepared_path=Path(prepared_path).resolve(strict=True)
        prep=verify_manifest(prepared_path)
        if prep.get('status')!='ENGINEERING_ADMITTED': raise ValueError('prepared record not admitted')
        protocol=strict_json((prepared_path/'protocol.json').read_text())
        validate_protocol(protocol)
        inputs=strict_json((prepared_path/'inputs.json').read_text())
        ids=strict_json((prepared_path/'binary-identities.json').read_text())
        ident=root_identity(); review=strict_json(Path(review_path).read_text())
        validate_review(review,ident['head'])
        prepared_manifest=digest(prepared_path/'manifest.json')
        auth=strict_json(Path(authorization_path).read_text())
        validate_authorization(auth,ident['head'],prepared_manifest)
        if (prep.get('head')!=ident['head'] or prep.get('protocol_sha256')!=digest(PROTOCOL) or
            verify_manifest(inputs['capture_path']).get('task_id')!='mjpc-adaptation-original-3s-v1' or
            digest(Path(inputs['capture_path'])/'manifest.json')!=inputs['capture_manifest_sha256'] or
            digest(Path(inputs['capture_path'])/'raw.jsonl')!=inputs['raw_sha256'] or
            model_identity()!=inputs['models']):
            raise ValueError('prepared head/protocol/raw capture identity changed')
        binaries={v:Path(ids[v]['path']) for v in ('original','fixed')}
        current={v:build_identity(binaries[v],v) for v in ('original','fixed')}
        if current!=ids: raise ValueError('paired binary identity changed')
        from tools.research.preflight import DEFAULT_PROCESS_NAMES,find_processes
        if find_processes(DEFAULT_PROCESS_NAMES+('go2_mjpc_controller_fd_original','go2_mjpc_controller_fd_fixed')):
            raise ValueError('stale Go2/native process before run')
        anchors={r['tick']:r for r in inputs['anchors']}; completed=[]; stop=None
        with EvidenceRun(Path(output),{'operation':'private_fd_duplicate_diagnostic'}) as run_record:
            run_record.result.update(scope='private_fd_duplicate_diagnostic',task_id=protocol['task_id'],
                head=ident['head'],prepared_manifest_sha256=prepared_manifest,
                optimizer_calls_max=8,private_total_upper_bound=TOTAL_UPPER,
                private_total_reserved_upper_bound=TOTAL_RESERVED,canonical_integration_steps=0)
            with wall_deadline(300):
                for item in trial_plan():
                    label=f"tick{item['tick']}_{item['variant']}_repeat{item['repeat']}"
                    try:
                        completed.append(run_trial(item,anchors[item['tick']],binaries,ids,run_record.path/label))
                    except BaseException as exc:
                        stop=f'{type(exc).__name__}: {exc}'
                        break
            status='DIAGNOSTIC_COMPLETE' if stop is None else 'STOPPED_INCOMPLETE'
            result={'schema':1,'status':status,'head':ident['head'],'protocol_sha256':digest(PROTOCOL),
                'input_sha256':digest(prepared_path/'inputs.json'),'binary_identities':ids,
                'trial_plan':trial_plan(),'models':inputs['models'],'completed_trials':completed,'repeat_comparisons':repeat_summary(completed),
                'optimizer_calls_completed':len(completed),
                'private_observed_upper_bound':sum(x['observation']['private_call_upper_bound'] for x in completed),
                'private_configured_reservation':len(completed)*RESERVATION,
                'private_total_upper_bound_max':TOTAL_UPPER,'private_total_reserved_upper_bound_max':TOTAL_RESERVED,
                'canonical_integration_steps':0,'seed':'not used (xfrc_std=0)',
                'scientific_gate':'none; observations only','stop_reason':stop}
            write_new(run_record.path/'RESULT.json',result)
            run_record.result.update(status=status,optimizer_calls_completed=len(completed),
                private_observed_upper_bound=result['private_observed_upper_bound'],
                private_configured_reservation=result['private_configured_reservation'],
                stop_reason=stop,result_path='RESULT.json')
    return str(Path(output)/'RESULT.json')

def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('plan')
    prep=sub.add_parser('prepare'); prep.add_argument('--capture',type=Path,default=CAPTURE)
    prep.add_argument('--original-binary',type=Path,required=True); prep.add_argument('--fixed-binary',type=Path,required=True)
    prep.add_argument('--output',type=Path,required=True)
    start=sub.add_parser('run'); start.add_argument('--prepared',type=Path,required=True)
    start.add_argument('--review',type=Path,required=True); start.add_argument('--authorization',type=Path,required=True)
    start.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.cmd=='plan': print(json.dumps({'bounds':derive_bounds(),'trials':trial_plan()},indent=2,sort_keys=True))
    elif a.cmd=='prepare': print(prepare(a.capture,a.original_binary,a.fixed_binary,a.output))
    else: print(run(a.prepared,a.review,a.authorization,a.output))

if __name__=='__main__': main()
