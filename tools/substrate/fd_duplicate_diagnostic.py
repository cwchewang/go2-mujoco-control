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

def default_run_record_paths(prepared_path):
    prepared=Path(prepared_path).resolve(strict=True)
    base=prepared.parent/(prepared.name+'_run_records')
    return {'review':base/'review.json','authorization':base/'authorization.json',
            'output':base/'result'}

def validate_run_record_paths(prepared_path,**paths):
    prepared=Path(prepared_path).resolve(strict=True)
    for label,value in paths.items():
        candidate=Path(value)
        lexical=candidate if candidate.is_absolute() else Path.cwd()/candidate
        lexical=Path(os.path.abspath(lexical))
        resolved=candidate.resolve(strict=False)
        if (lexical==prepared or lexical.is_relative_to(prepared) or
            resolved==prepared or resolved.is_relative_to(prepared)):
            raise ValueError(f'{label} path must be outside prepared bundle')

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

def candidate_contract(ready):
    protocol=strict_json(PROTOCOL.read_text())
    validate_protocol(protocol)
    expected={'ready':True,'protocol':3,'nq':19,'nv':18,'nu':12,
        'worker_count':protocol['workers'],'horizon_steps':protocol['horizon_steps'],
        'planner':'MJPC iLQG','warning_channel':'stderr',
        'policy_freshness':'current_candidate_required',
        'canonical_evaluation_plant_modified':False,
        'compatibility_correction':'private_model_mjBIAS_AFFINE','source_nominal_biastype':'mjBIAS_NONE',
        'ground_miss_handling':'rollout_warning_failure','gait_switch':'Manual','gait':'Trot'}
    if (not isinstance(ready,dict) or
        any(type(ready.get(k)) is not type(v) or ready[k]!=v for k,v in expected.items()) or
        not finite(ready.get('planner_dt')) or
        not math.isclose(ready['planner_dt'],protocol['planner_dt_s'],rel_tol=0,abs_tol=1e-12)):
        raise ValueError('native startup configuration mismatch')
    for name in ('position_lower','position_upper','kp','kd'):
        if not vector(ready.get(name),ready['nu']):
            raise ValueError('native startup actuator dimensions mismatch')
    if (not isinstance(ready.get('joint_names'),list) or len(ready['joint_names'])!=ready['nu'] or
        any(not isinstance(x,str) or not x for x in ready['joint_names']) or
        len(set(ready['joint_names']))!=ready['nu'] or
        ready['kp']!=[60]*ready['nu'] or ready['kd']!=[5]*ready['nu'] or
        any(lo>=hi for lo,hi in zip(ready['position_lower'],ready['position_upper']))):
        raise ValueError('native startup actuator identity mismatch')
    return {'knots':ready['horizon_steps'],'qpos':ready['nq'],'qvel':ready['nv'],
            'action':ready['nu'],'workers':ready['worker_count'],
            'dt':ready['planner_dt'],'rollouts':protocol['nominal_rollouts']}

def finite(value):
    return type(value) in (int,float) and math.isfinite(value)

def vector(value,size):
    return isinstance(value,list) and len(value)==size and all(finite(x) for x in value)

def validate_response(variant,response,trace,predictions,stderr_bytes,anchor,ready):
    if variant not in ('original','fixed'): raise ValueError('invalid FD variant')
    c=candidate_contract(ready)
    if not isinstance(response,dict) or not isinstance(trace,dict):
        raise ValueError('response/trace must be objects')
    fd_calls,fd_upper=(OLD_FD if variant=='original' else FIXED_FD)
    diag=response.get('diagnostic',{})
    if not isinstance(diag,dict) or not isinstance(predictions,list):
        raise ValueError('diagnostic/prediction fields malformed')
    if (response.get('ok') is not True or response.get('replanned') is not True or
        response.get('current_rollout_valid') is not True or diag.get('policy_id')!=1 or
        diag.get('fd_call_count')!=fd_calls or diag.get('fd_step_upper_bound_count')!=fd_upper or
        diag.get('rollout_mj_step_count')!=ROLLOUT_STEPS or
        diag.get('private_step_upper_bound_reserved')!=RESERVATION or
        diag.get('private_step_limit')!=LIMIT or stderr_bytes!=0 or
        any(type(diag.get(k)) is not int for k in ('policy_id','fd_call_count',
            'fd_step_upper_bound_count','rollout_mj_step_count',
            'private_step_upper_bound_reserved','private_step_limit'))):
        raise ValueError('native warning, candidate, identity or private budget mismatch')
    events=trace.get('events')
    t34=2 if variant=='original' else 1
    last=c['knots']-1
    expected_knots=([*range(last),last-1,last] if variant=='original' else list(range(c['knots'])))
    if (trace.get('index_count')!=fd_calls or not isinstance(events,list) or len(events)!=fd_calls or
        [e.get('t') for e in events]!=expected_knots or
        sum(e.get('t')==34 for e in events)!=t34 or
        any(type(e.get('t')) is not int or type(e.get('worker')) is not int or e['worker'] not in range(c['workers']) or
            type(e.get('start_ns')) is not int or type(e.get('end_ns')) is not int or
            e['start_ns']>=e['end_ns'] for e in events) or
        not re.fullmatch(r'[0-9a-f]{16}',trace.get('jacobian_t34_fnv1a64','')) or
        len(predictions)!=1 or not isinstance(predictions[0],dict) or
        type(predictions[0].get('policy_id')) is not int or predictions[0].get('policy_id')!=1 or
        type(predictions[0].get('candidate_id')) is not int or
        predictions[0]['candidate_id'] not in range(c['rollouts']) or
        not finite(predictions[0].get('anchor_time_s')) or
        not math.isclose(predictions[0]['anchor_time_s'],anchor['time_s'],rel_tol=0,abs_tol=1e-12) or
        not finite(response.get('cost')) or
        not isinstance(response.get('q_des'),list) or len(response['q_des'])!=c['action'] or
        any(type(x) not in (int,float) or not math.isfinite(x) for x in response['q_des'])):
        raise ValueError('FD worker/knot/Jacobian or candidate trace mismatch')
    if 'call_index' in trace:
        if trace.get('call_index') != 1 or any(e.get('call_index') != 1 for e in events):
            raise ValueError('FD trace optimizer-call identity mismatch')
        for event in events:
            for key in ('warmstart_before_fnv1a64','warmstart_after_fnv1a64'):
                value=event.get(key)
                if not isinstance(value,str) or not re.fullmatch(r'[0-9a-f]{16}',value):
                    raise ValueError('FD warmstart hash missing or malformed')
            for key in ('warmstart_before_norm','warmstart_before_max_abs',
                        'warmstart_after_norm','warmstart_after_max_abs'):
                if not finite(event.get(key)) or event[key] < 0:
                    raise ValueError('FD warmstart summary invalid')
    prediction=predictions[0]
    if 'planner_history' in prediction:
        history=prediction['planner_history']
        if (not isinstance(history,dict) or history.get('call_index') != 1 or
            set(history) != {'call_index','pre_policy','pre_previous_policy','post_policy','selected_trajectory','worker_warmstart'}):
            raise ValueError('planner history summary missing or inconsistent')
        for name in ('pre_policy','pre_previous_policy','post_policy','selected_trajectory'):
            summary=history[name]
            if (not isinstance(summary,dict) or summary.get('finite') is not True or
                summary.get('return_finite') is not True or not finite(summary.get('total_return')) or
                type(summary.get('horizon')) is not int or type(summary.get('dim_state')) is not int or
                type(summary.get('dim_action')) is not int or
                not re.fullmatch(r'[0-9a-f]{16}',summary.get('fnv1a64',''))):
                raise ValueError('planner trajectory summary invalid')
        workers=history.get('worker_warmstart')
        if not isinstance(workers,dict) or set(workers)!={'pre','post'}:
            raise ValueError('worker warmstart boundary summary missing')
        for side in ('pre','post'):
            values=workers[side]
            if not isinstance(values,list) or any(
                not isinstance(v,dict) or type(v.get('worker')) is not int or
                v.get('finite') is not True or not finite(v.get('norm')) or v['norm']<0 or
                not finite(v.get('max_abs')) or v['max_abs']<0 or
                not re.fullmatch(r'[0-9a-f]{16}',v.get('fnv1a64',''))
                for v in values):
                raise ValueError('worker warmstart summary invalid')
    if (prediction.get('mode')!=variant or
        prediction.get('optimization_model_id')!=variant+'-go2-soft-v1' or
        prediction.get('contact_semantics')!='selected_states_forward_reconstruction_smoothed_private_model' or
        any(not finite(response.get(k)) or not math.isclose(response[k],v,rel_tol=0,abs_tol=1e-12)
            for k,v in (('time_s',anchor['time_s']),('vx',anchor['command'][0]),('wz',anchor['command'][2])))):
        raise ValueError('candidate mode/response identity mismatch')
    accounting=prediction.get('private_accounting')
    expected={'fd_call_count':fd_calls,'fd_step_upper_bound_count':fd_upper,
              'rollout_mj_step_count':ROLLOUT_STEPS,'reserved_step_upper_bound':RESERVATION}
    if not isinstance(accounting,dict) or any(type(accounting.get(k)) is not int or accounting[k]!=v for k,v in expected.items()):
        raise ValueError('candidate private accounting mismatch')
    states=prediction.get('states')
    if not isinstance(states,list) or len(states)!=c['knots']:
        raise ValueError('candidate horizon/state dimensions mismatch')
    for t,state in enumerate(states):
        if (not isinstance(state,dict) or not vector(state.get('qpos'),c['qpos']) or
            not vector(state.get('qvel'),c['qvel']) or
            not vector(state.get('nominal_position_action'),c['action']) or
            not finite(state.get('time_s')) or
            not math.isclose(state['time_s'],anchor['time_s']+t*c['dt'],rel_tol=0,abs_tol=1e-12) or
            not isinstance(state.get('active_contacts'),list)):
            raise ValueError('candidate state/action dimensions or time mismatch')
        for contact in state['active_contacts']:
            if (not isinstance(contact,dict) or
                not isinstance(contact.get('geom_ids'),list) or len(contact['geom_ids'])!=2 or
                any(type(x) is not int or x<0 for x in contact['geom_ids']) or
                not isinstance(contact.get('geom_names'),list) or len(contact['geom_names'])!=2 or
                any(not isinstance(x,str) for x in contact['geom_names']) or
                not finite(contact.get('distance_m'))):
                raise ValueError('candidate contact fields mismatch')
    first=states[0]
    if any(not math.isclose(float(x),float(y),rel_tol=0,abs_tol=1e-12)
           for x,y in zip(first['qpos']+first['qvel'],anchor['qpos']+anchor['qvel'])):
        raise ValueError('candidate initial state does not match fixed input anchor')
    events34=[e for e in events if e['t']==34]
    overlap=len(events34)==2 and events34[0]['start_ns']<events34[1]['end_ns'] and events34[1]['start_ns']<events34[0]['end_ns']
    return {'fd_calls':fd_calls,'fd_step_upper_bound':fd_upper,'rollout_steps':ROLLOUT_STEPS,
        'private_call_upper_bound':OLD_PRIVATE if variant=='original' else FIXED_PRIVATE,
        'jacobian_t34_fnv1a64':trace['jacobian_t34_fnv1a64'],
        't34_overlap':overlap,'t34_workers':[e['worker'] for e in events34],
        'candidate_id':predictions[0]['candidate_id'],'cost':response.get('cost'),
        'q_des':response.get('q_des')}

def _packet(anchor,replan=True):
    values=[anchor['time_s'],*anchor['command'],*anchor['qpos'],*anchor['qvel']]
    return 'step '+('1' if replan else '0')+' '+' '.join(format(float(x),'.17g') for x in values)

def parse_trial_logs(trial,anchor,identities,directory):
    directory=Path(directory)
    rows=[strict_json(x) for x in (directory/'native.jsonl').read_text().splitlines()]
    if (len(rows)!=2 or set(rows[0])!={'ready'} or set(rows[1])!={'request','response'} or
        rows[1]['request']!=_packet(anchor)):
        raise ValueError('native request/response log mismatch')
    traces=[strict_json(x) for x in (directory/'fd-trace.jsonl').read_text().splitlines()]
    candidates=[strict_json(x) for x in (directory/'predictions.jsonl').read_text().splitlines()]
    observation=validate_response(trial['variant'],rows[1]['response'],
        traces[0] if len(traces)==1 else {},candidates,
        (directory/'native.stderr.log').stat().st_size,anchor,rows[0]['ready'])
    return {**trial,'binary_identity':identities[trial['variant']],
        'logs':{'native':'native.jsonl','stderr':'native.stderr.log',
                'fd_worker_knots':'fd-trace.jsonl','candidate':'predictions.jsonl'},
        'observation':observation}

def trial_accounting(trial,directory):
    directory=Path(directory); rows=[]; response=None
    try:
        rows=[strict_json(x) for x in (directory/'native.jsonl').read_text().splitlines()]
        response=next((r['response'] for r in rows if isinstance(r,dict) and 'response' in r),None)
    except (OSError,ValueError): pass
    attempted=(directory/'optimizer-attempt.json').exists() or any(isinstance(r,dict) and 'request' in r for r in rows)
    raw=response.get('diagnostic') if isinstance(response,dict) else None
    keys=('fd_call_count','fd_step_upper_bound_count','rollout_mj_step_count','private_step_upper_bound_reserved')
    known=isinstance(raw,dict) and all(type(raw.get(k)) is int and raw[k]>=0 for k in keys)
    return {**trial,'optimizer_call_attempted':attempted,'budget_known':known,
        'raw_private_accounting':raw,'accounting_source':'native.jsonl response.diagnostic' if known else 'unavailable',
        'private_observed_upper_bound':raw['fd_step_upper_bound_count']+raw['rollout_mj_step_count'] if known else None,
        'private_configured_reservation':max(RESERVATION,raw['private_step_upper_bound_reserved']) if known and attempted else (RESERVATION if attempted else 0),
        'private_attempted_upper_bound':(OLD_PRIVATE if trial['variant']=='original' else FIXED_PRIVATE) if attempted else 0}

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
        candidate_contract(ready)
        write_new(directory/'optimizer-attempt.json',{'optimizer_call_attempted':True,
            'variant':trial['variant'],'reserved_upper_bound':RESERVATION})
        response=transport.request(packet,30)
        with native_log.open('a') as f:
            f.write(json.dumps({'request':packet,'response':response},sort_keys=True,allow_nan=False)+'\n')
            f.flush(); os.fsync(f.fileno())
    finally:
        transport.close()
    stderr=transport.diagnostics()
    if stderr['stderr_read_error'] or stderr['stderr_bytes']:
        raise ValueError('warning or stderr drain failure')
    return parse_trial_logs(trial,anchor,identities,directory)

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

def collect_trials(plan,anchors,ids,directory,runner):
    completed=[]; records=[]; stop=None
    for item in plan:
        label=f"tick{item['tick']}_{item['variant']}_repeat{item['repeat']}"
        trial_dir=Path(directory)/label; error=None
        try: completed.append(runner(item,anchors[item['tick']],ids,trial_dir))
        except BaseException as exc: error=f'{type(exc).__name__}: {exc}'; stop=error
        records.append({**trial_accounting(item,trial_dir),
            'status':'REJECTED' if error else 'ACCEPTED','error':error})
        if error: break
    return completed,records,stop

def make_result(ident,inputs,ids,plan,completed,records,stop,prepared_path,offline=False):
    attempted=[r for r in records if r['optimizer_call_attempted']]
    unknown=sum(not r['budget_known'] for r in attempted)
    return {'schema':2,'status':'STOPPED_INCOMPLETE' if stop else ('OFFLINE_REPLAY_COMPLETE' if offline else 'DIAGNOSTIC_COMPLETE'),
        'head':ident['head'],'protocol_sha256':digest(PROTOCOL),'input_sha256':digest(Path(prepared_path)/'inputs.json'),
        'binary_identities':ids,'trial_plan':plan,'models':inputs['models'],
        'completed_trials':completed,'trial_records':records,'attempted_trials':attempted,
        'repeat_comparisons':repeat_summary(completed),'optimizer_calls_attempted':len(attempted),
        'optimizer_calls_completed':len(completed),'new_optimizer_calls':0 if offline else len(attempted),
        'private_observed_upper_bound':None if unknown else sum(r['private_observed_upper_bound'] for r in attempted),
        'private_budget_unknown_trials':unknown,'private_attempted_upper_bound':sum(r['private_attempted_upper_bound'] for r in attempted),
        'private_configured_reservation':sum(r['private_configured_reservation'] for r in attempted),
        'private_total_upper_bound_max':TOTAL_UPPER,'private_total_reserved_upper_bound_max':TOTAL_RESERVED,
        'canonical_integration_steps':0,'seed':'not used (xfrc_std=0)',
        'scientific_gate':'none; observations only','stop_reason':stop}

def record_result(run_record,result,offline=False):
    write_new(run_record.path/'RESULT.json',result)
    for k in ('status','optimizer_calls_attempted','optimizer_calls_completed','new_optimizer_calls',
        'private_observed_upper_bound','private_budget_unknown_trials','private_attempted_upper_bound',
        'private_configured_reservation','stop_reason'): run_record.result[k]=result[k]
    run_record.result.update(capability_status='OFFLINE_REPLAY_ONLY' if offline else ('PRIVATE_DIAGNOSTIC_EXECUTED' if result['optimizer_calls_attempted'] else 'NOT_RUN'),result_path='RESULT.json')

def run(prepared_path,review_path=None,authorization_path=None,output=None):
    with experiment_lock():
        prepared_path=Path(prepared_path).resolve(strict=True)
        defaults=default_run_record_paths(prepared_path)
        review_path=Path(review_path) if review_path is not None else defaults['review']
        authorization_path=(Path(authorization_path) if authorization_path is not None
                            else defaults['authorization'])
        output=Path(output) if output is not None else defaults['output']
        validate_run_record_paths(prepared_path,review=review_path,
            authorization=authorization_path,output=output)
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
        anchors={r['tick']:r for r in inputs['anchors']}
        with EvidenceRun(Path(output),{'operation':'private_fd_duplicate_diagnostic'}) as run_record:
            run_record.result.update(scope='private_fd_duplicate_diagnostic',task_id=protocol['task_id'],
                head=ident['head'],prepared_manifest_sha256=prepared_manifest,optimizer_calls_max=8,
                private_total_upper_bound=TOTAL_UPPER,private_total_reserved_upper_bound=TOTAL_RESERVED,canonical_integration_steps=0)
            def live_runner(item,anchor,identities,directory):
                return run_trial(item,anchor,binaries,identities,directory)
            with wall_deadline(300):
                completed,records,stop=collect_trials(trial_plan(),anchors,ids,run_record.path,live_runner)
            result=make_result(ident,inputs,ids,trial_plan(),completed,records,stop,prepared_path)
            record_result(run_record,result)
    return str(Path(output)/'RESULT.json')

def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('plan')
    prep=sub.add_parser('prepare'); prep.add_argument('--capture',type=Path,default=CAPTURE)
    prep.add_argument('--original-binary',type=Path,required=True); prep.add_argument('--fixed-binary',type=Path,required=True)
    prep.add_argument('--output',type=Path,required=True)
    start=sub.add_parser('run'); start.add_argument('--prepared',type=Path,required=True)
    start.add_argument('--review',type=Path,help='external exact-head review JSON (default: sibling run-record directory)')
    start.add_argument('--authorization',type=Path,help='external user authorization JSON (default: sibling run-record directory)')
    start.add_argument('--output',type=Path,help='external result directory (default: sibling run-record directory)')
    a=p.parse_args()
    if a.cmd=='plan': print(json.dumps({'bounds':derive_bounds(),'trials':trial_plan()},indent=2,sort_keys=True))
    elif a.cmd=='prepare': print(prepare(a.capture,a.original_binary,a.fixed_binary,a.output))
    else: print(run(a.prepared,a.review,a.authorization,a.output))

if __name__=='__main__': main()
