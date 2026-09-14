#!/usr/bin/env python3
"""Audit the Phase1 pre-motion lockstep startup checkpoint."""
import csv, hashlib, itertools, math, statistics
from bisect import bisect_left
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
RUN_ROOT=ROOT/"example/cpp/experiments/_runs/phase1_lockstep_premotion_startup_20260914"
OUT=ROOT/"docs/validation/phase1_lockstep_premotion_startup_20260914"
RUNS=("L1","L2","L3"); DT=.010; TOL=.010; EPS=1e-12
KEYS=("measured","applied","excess","roll","pitch","physical_contact_count",
      "physical_contact_mask","controller_contact_mask","gait_phase")

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def rows(p):
    with p.open(newline="",encoding="utf-8",errors="replace") as f:
        return list(csv.DictReader(f))

def meta(p):
    return dict(x.split("=",1) for x in p.read_text(encoding="utf-8",
        errors="replace").splitlines() if "=" in x)

def num(r,k,d=float("nan")):
    try: return float(r.get(k,""))
    except (TypeError,ValueError): return d

def integer(r,k,d=0):
    try: return int(float(r.get(k,"")))
    except (TypeError,ValueError): return d

def finite(v): return [x for x in v if math.isfinite(x)]

def med(v):
    v=finite(v)
    return statistics.median(v) if v else float("nan")

def pct(v,q):
    v=sorted(finite(v))
    if not v: return float("nan")
    z=(len(v)-1)*q; lo=int(z); hi=min(lo+1,len(v)-1)
    return v[lo]+(v[hi]-v[lo])*(z-lo)

def fmt(x):
    if x is None or (isinstance(x,float) and not math.isfinite(x)): return ""
    return "%.12g"%x if isinstance(x,float) else str(x)

def count(v):
    d={}
    for x in v: d[x]=d.get(x,0)+1
    return ",".join("%s:%s"%(k,d[k]) for k in sorted(d,key=lambda x:int(x)))

def gate(run,name,ok,detail):
    return {"run_id":run,"gate":name,"status":"PASS" if ok else "FAIL",
            "detail":detail}

def write(p,data,fields):
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n")
        w.writeheader(); w.writerows(data)

def cmask(r):
    return integer(r,"contact_FR")|(integer(r,"contact_FL")<<1)|(
        integer(r,"contact_RR")<<2)|(integer(r,"contact_RL")<<3)

def nearest(rs,ts,t):
    if not rs: return None
    i=bisect_left(ts,t)
    choices=([i] if i<len(rs) else [])+([i-1] if i else [])
    if not choices: return None
    j=min(choices,key=lambda k:abs(ts[k]-t))
    return rs[j] if abs(ts[j]-t)<=TOL+EPS else None

def diff(a,b,k):
    if k=="measured": return abs(num(a,"velocity_command_measured_mps")-num(b,"velocity_command_measured_mps"))
    if k=="applied": return abs(num(a,"velocity_command_applied_mps")-num(b,"velocity_command_applied_mps"))
    if k=="excess":
        la=num(a,"velocity_command_measured_mps")-num(a,"velocity_command_applied_mps")
        lb=num(b,"velocity_command_measured_mps")-num(b,"velocity_command_applied_mps")
        return abs(la-lb)
    if k=="roll": return abs(math.degrees(num(a,"imu_roll_rad"))-math.degrees(num(b,"imu_roll_rad")))
    if k=="pitch": return abs(math.degrees(num(a,"imu_pitch_rad"))-math.degrees(num(b,"imu_pitch_rad")))
    if k=="physical_contact_count": return abs(integer(a,"contact_count")-integer(b,"contact_count"))
    if k=="physical_contact_mask": return abs(cmask(a)-cmask(b))
    if k=="controller_contact_mask": return abs(integer(a,"diag_contact_mask")-integer(b,"diag_contact_mask"))
    if k=="gait_phase": return abs(num(a,"phase")-num(b,"phase"))
    raise KeyError(k)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    info={}; hs={}; cs={}; ds={}; pg=[]; active_end={}; first_gate_time={}; controller_handoff_tick={}; excess_median_value={}
    for run in RUNS:
        d=RUN_ROOT/run; m=meta(d/"run_metadata.txt")
        dg=sorted(rows(d/"data.csv.lockstep_publish.csv"),
                  key=lambda r:integer(r,"publish_index"))
        tr=[r for r in rows(d/"lockstep_trace.csv") if r.get("phase")=="lockstep"]
        hp=d/"lockstep_handoff.csv"; h=rows(hp)[0]; hb=Path(str(hp)+".bin")
        first=next((r for r in dg if r.get("handoff_prepared")=="1" and
                    r.get("writer_branch")=="gated"),None)
        if first is None: raise RuntimeError("%s has no gated handoff row"%run)
        fi=integer(first,"publish_index"); ht=integer(h,"sim_tick_ms"); ct=integer(first,"handoff_state_tick")
        controller_handoff_tick[run]=ct
        gated=[r for r in dg if integer(r,"publish_index")>=fi and
               r.get("writer_branch")=="gated"]
        gt=[integer(r,"state_tick") for r in gated]; groups={}
        for r in gated: groups.setdefault(integer(r,"state_tick"),[]).append(r)
        dupg=sum(len(v)>1 for v in groups.values())
        dupe=sum(max(0,len(v)-1) for v in groups.values())
        tt=[integer(r,"sim_tick_ms") for r in tr]
        td=[b-a for a,b in zip(tt,tt[1:])]
        cd=[integer(r,"cmd_seq_at_ready")-integer(r,"cmd_seq_at_publish") for r in tr]
        slog=(d/"simulator.log").read_text(encoding="utf-8",errors="replace")
        clog=(d/"controller.log").read_text(encoding="utf-8",errors="replace")
        marker="SIM_LOCKSTEP_FAIL_CLOSED" in slog or "TROT_LOCKSTEP_WRITER_FAIL_CLOSED" in clog
        early=any(integer(r,"stop_requested")==1 or integer(r,"sequence_finished")==1
                  for r in dg if num(r,"running_time_s")<40)
        free=any(r.get("handoff_prepared")=="1" and r.get("writer_branch")!="gated" for r in dg)
        active_pre=any(integer(r,"state_tick")<ht and integer(r,"gait_started")==1 for r in dg)
        first_ok=integer(first,"state_tick")==ht and integer(first,"handoff_state_tick")==ht and integer(first,"gait_started")==0
        gates=[
          gate(run,"trace_present",bool(tr),"lockstep_rows=%d"%len(tr)),
          gate(run,"constant_2ms_after_handoff",bool(td) and set(td)=={2},"dt_ms=%s"%sorted(set(td))),
          gate(run,"no_protocol_violations",bool(tr) and all(integer(r,"violations")==0 for r in tr),"violations=%s"%sorted(set(integer(r,"violations") for r in tr))),
          gate(run,"ack_state_matches_published_tick",bool(tr) and all(integer(r,"ack_state_seq")==integer(r,"sim_tick_ms") for r in tr),"intervals=%d"%len(tr)),
          gate(run,"exact_pair_trigger",bool(tr) and all(integer(r,"exchange_trigger")==3 for r in tr),"triggers=%s"%sorted(set(integer(r,"exchange_trigger") for r in tr))),
          gate(run,"one_command_update_per_state_tick",bool(tr) and all(x==1 and integer(r,"ack_cmd_seq")==integer(r,"cmd_seq_at_ready") for x,r in zip(cd,tr)),"delta_counts=%s"%count(cd)),
          gate(run,"no_same_tick_duplicate_active_lowcmd",dupe==0,"duplicate_groups=%d duplicate_extra_rows=%d"%(dupg,dupe)),
          gate(run,"no_fail_closed_marker",not marker,"marker=%s"%marker),
          gate(run,"premotion_handoff_before_active_motion",not free and not active_pre,"free_after_handoff=%s active_before_handoff=%s"%(free,active_pre)),
          gate(run,"first_active_command_consumes_handoff",first_ok,"first_state_tick=%d handoff_state_tick=%d gait_started=%d"%(integer(first,"state_tick"),integer(first,"handoff_state_tick"),integer(first,"gait_started"))),
          gate(run,"controller_handoff_tick_matches_simulator",ct==ht,"controller_handoff_tick=%d simulator_handoff_tick=%d"%(ct,ht)),
          gate(run,"controller_gated_ticks_strictly_new",bool(gated) and all(b-a==2 for a,b in zip(gt,gt[1:])),"gated_rows=%d"%len(gated))]
        pg+=gates
        c=rows(d/"data.csv"); cs[run]=c; ds[run]=dg
        active=[r for r in c if integer(r,"velocity_command_active")==1]
        at=[num(r,"diag_active_relative_time_s") for r in active]
        end=max(finite(at),default=float("nan"))
        first_gate_time[run]=num(first,"running_time_s")
        active_end[run]=end
        win=[r for r in active if 32<=num(r,"diag_active_relative_time_s")<33]
        ex=[num(r,"velocity_command_measured_mps")-num(r,"velocity_command_applied_mps") for r in win]
        excess_median_value[run]=med(ex)
        wbc=[num(r,"wbc_full_requested_acc_x_mps2") for r in win]
        srbd=[num(r,"wbc_full_srbd_acc_x_mps2") for r in win]
        ident=[num(r,"wbc_full_id_qdd_x_mps2") for r in win]
        regimes=sorted(set(r.get("velocity_command_gait_regime","") for r in win))
        physical=math.isfinite(end) and end>=40 and m.get("safety_status")=="0" and not early and bool(win) and regimes==["continuous-trot"] and .15<=med(ex)<=.35 and med(wbc)<0 and med(srbd)<0 and med(ident)<0
        hs[run]={"steps":integer(h,"pre_motion_steps"),"tick":ht,"time":num(h,"sim_time_s"),"nq":integer(h,"nq"),"nv":integer(h,"nv"),"nu":integer(h,"nu"),"sha":sha(hb),
                 "qpos":[num(h,"qpos_%d"%i) for i in range(integer(h,"nq"))],
                 "qvel":[num(h,"qvel_%d"%i) for i in range(integer(h,"nv"))],
                 "aq":[num(h,"actuated_q_%d"%i) for i in range(integer(h,"nu"))],
                 "adq":[num(h,"actuated_dq_%d"%i) for i in range(integer(h,"nu"))]}
        info[run]={"run_id":run,"source_git_head":m.get("git_head",""),"git_branch":m.get("git_branch",""),"git_dirty":m.get("git_dirty",""),
          "simulator_sha256":m.get("simulator_sha256",""),"controller_sha256":m.get("controller_sha256",""),"scene_sha256":m.get("scene_sha256",""),
          "profile_sha256":sha(ROOT/"example/cpp/configs/phase1_velocity_varying.csv"),"domain_id":m.get("domain_id",""),
          "active_relative_duration_s":fmt(end),"active_rows":len(active),"window_rows_32_33":len(win),
          "measured_median_mps":fmt(med([num(r,"velocity_command_measured_mps") for r in win])),"applied_median_mps":fmt(med([num(r,"velocity_command_applied_mps") for r in win])),
          "excess_median_mps":fmt(med(ex)),"wbc_desired_ax_median_mps2":fmt(med(wbc)),"srbd_ax_median_mps2":fmt(med(srbd)),"id_qdd_x_median_mps2":fmt(med(ident)),
          "gait_regimes_32_33":"|".join(regimes),"controller_status":m.get("controller_status",""),"safety_status":m.get("safety_status",""),"quality_status":m.get("quality_status",""),
          "analysis_status":m.get("analysis_status",""),"ground_truth_status":m.get("ground_truth_status",""),"dynamics_status":m.get("dynamics_status",""),"completion_status":m.get("completion_status",""),
          "trace_rows":len(tr),"gated_rows":len(gated),"first_gated_publish_index":integer(first,"publish_index"),"first_gated_state_tick":integer(first,"state_tick"),"first_gated_cmd_seq":integer(first,"lockstep_cmd_seq"),"first_gated_running_time_s":fmt(num(first,"running_time_s")),"handoff_state_tick":ht,"controller_handoff_state_tick":ct,"handoff_binary_sha256":sha(hb),"duplicate_groups":dupg,"duplicate_extra_rows":dupe,
          "protocol_status":"PASS" if all(x["status"]=="PASS" for x in gates) else "FAIL","physical_status":"PASS" if physical else "FAIL"}
    pairs=list(itertools.combinations(RUNS,2)); ph={}
    for l,r in pairs:
        ph[l,r]={k:max(abs(a-b) for a,b in zip(hs[l][k],hs[r][k])) for k in ("qpos","qvel","aq","adq")}
    mx={k:max(v[k] for v in ph.values()) for k in ("qpos","qvel","aq","adq")}
    exact=len({hs[r]["sha"] for r in RUNS})==1
    controller_ticks_match=all(controller_handoff_tick[r]==hs[r]["tick"] for r in RUNS)
    handoff_ok=exact and all(v<=EPS for v in mx.values()) and controller_ticks_match
    hf=["run_id","pre_motion_steps","sim_tick_ms","sim_time_s","nq","nv","nu","binary_sha256","pairwise_max_qpos_abs","pairwise_max_qvel_abs","pairwise_max_actuated_q_abs","pairwise_max_actuated_dq_abs","controller_handoff_state_tick","controller_first_gated_state_tick","controller_first_gated_gait_started"]
    hr=[]
    for run in RUNS:
        first=next(r for r in ds[run] if integer(r,"publish_index")==info[run]["first_gated_publish_index"])
        hr.append({"run_id":run,"pre_motion_steps":hs[run]["steps"],"sim_tick_ms":hs[run]["tick"],"sim_time_s":fmt(hs[run]["time"]),"nq":hs[run]["nq"],"nv":hs[run]["nv"],"nu":hs[run]["nu"],"binary_sha256":hs[run]["sha"],"pairwise_max_qpos_abs":fmt(mx["qpos"]),"pairwise_max_qvel_abs":fmt(mx["qvel"]),"pairwise_max_actuated_q_abs":fmt(mx["aq"]),"pairwise_max_actuated_dq_abs":fmt(mx["adq"]),"controller_handoff_state_tick":controller_handoff_tick[run],"controller_first_gated_state_tick":info[run]["first_gated_state_tick"],"controller_first_gated_gait_started":integer(first,"gait_started")})
    hr.append({"run_id":"PAIRWISE_MAX","binary_sha256":"IDENTICAL" if exact else "DIFFERENT","pairwise_max_qpos_abs":fmt(mx["qpos"]),"pairwise_max_qvel_abs":fmt(mx["qvel"]),"pairwise_max_actuated_q_abs":fmt(mx["aq"]),"pairwise_max_actuated_dq_abs":fmt(mx["adq"])})
    write(OUT/"handoff_states.csv",hr,hf)
    for run in RUNS: pg.append(gate(run,"handoff_record_present",True,"sim_tick_ms=%d binary=%s"%(hs[run]["tick"],hs[run]["sha"])))
    pg += [gate("ALL","handoff_exact_binary_sha256",exact,"sha256_count=%d"%len({hs[r]["sha"] for r in RUNS})),gate("ALL","handoff_qpos_max_abs_le_1e-12",mx["qpos"]<=EPS,"max_abs=%s"%fmt(mx["qpos"])),gate("ALL","handoff_qvel_max_abs_le_1e-12",mx["qvel"]<=EPS,"max_abs=%s"%fmt(mx["qvel"])),gate("ALL","handoff_actuated_q_max_abs_le_1e-12",mx["aq"]<=EPS,"max_abs=%s"%fmt(mx["aq"])),gate("ALL","handoff_actuated_dq_max_abs_le_1e-12",mx["adq"]<=EPS,"max_abs=%s"%fmt(mx["adq"]))]
    ab={}
    starts=[first_gate_time[r] for r in RUNS if math.isfinite(first_gate_time[r])]
    ends=[active_end[r] for r in RUNS if math.isfinite(active_end[r])]
    for run in RUNS:
        ab[run]=sorted([r for r in cs[run] if integer(r,"velocity_command_active")==1],
                       key=lambda r:num(r,"diag_active_relative_time_s"))
    alignment_ok=len(starts)==len(RUNS) and len(ends)==len(RUNS) and all(ab[r] for r in RUNS)
    if alignment_ok:
        start=max(max(starts),max(num(ab[r][0],"diag_active_relative_time_s") for r in RUNS))
        start=math.ceil(start/DT-EPS)*DT
        end=math.floor(min(ends)/DT+EPS)*DT
        points=max(0,int(round((end-start)/DT))+1)
        aligned={}
        for run in RUNS:
            ts=[num(r,"diag_active_relative_time_s") for r in ab[run]]
            aligned[run]=[nearest(ab[run],ts,start+i*DT) for i in range(points)]
            if any(r is None for r in aligned[run]):
                alignment_ok=False
                break
    if not alignment_ok:
        start=float("nan"); end=float("nan"); points=0
    pf=["pair","grid_dt_s","max_nearest_tolerance_s",
        "common_active_relative_start_s","common_active_relative_end_s","grid_points"]
    pf += ["%s_%s_abs_diff"%(k,s) for k in KEYS for s in ("p50","p95","max")]
    pf += ["first_sustained_divergence_s",
           "first_sustained_divergence_before_40s"]
    pr=[]
    for l,r in pairs:
        z={"pair":l+"__"+r,"grid_dt_s":fmt(DT),
           "max_nearest_tolerance_s":fmt(TOL),
           "common_active_relative_start_s":fmt(start),
           "common_active_relative_end_s":fmt(end),"grid_points":points}
        if not alignment_ok:
            for k in KEYS:
                for s in ("p50","p95","max"):
                    z["%s_%s_abs_diff"%(k,s)]=""
            z["first_sustained_divergence_s"]=""; z["first_sustained_divergence_before_40s"]=""
            pr.append(z)
            continue
        for k in KEYS:
            v=[diff(a,b,k) for a,b in zip(aligned[l],aligned[r])]
            z["%s_p50_abs_diff"%k]=fmt(pct(v,.5))
            z["%s_p95_abs_diff"%k]=fmt(pct(v,.95))
            z["%s_max_abs_diff"%k]=fmt(max(finite(v),default=float("nan")))
        bad=[diff(a,b,"measured")>.05 or diff(a,b,"roll")>2 or
             diff(a,b,"pitch")>2 for a,b in zip(aligned[l],aligned[r])]
        streak=0; first_any=None; first_before=None
        for i,is_bad in enumerate(bad):
            streak=streak+1 if is_bad else 0
            if streak>=10:
                onset=start+(i-9)*DT
                if first_any is None: first_any=onset
                if onset<40 and first_before is None: first_before=onset
        z["first_sustained_divergence_s"]=fmt(first_any)
        z["first_sustained_divergence_before_40s"]=fmt(first_before)
        pr.append(z)
    write(OUT/"pairwise.csv",pr,pf)
    sf=["run_id","source_git_head","git_branch","git_dirty","simulator_sha256",
        "controller_sha256","scene_sha256","profile_sha256","domain_id",
        "active_relative_duration_s","active_rows","window_rows_32_33",
        "measured_median_mps","applied_median_mps","excess_median_mps",
        "wbc_desired_ax_median_mps2","srbd_ax_median_mps2",
        "id_qdd_x_median_mps2","gait_regimes_32_33","controller_status",
        "safety_status","quality_status","analysis_status","ground_truth_status",
        "dynamics_status","completion_status","trace_rows","gated_rows",
        "first_gated_publish_index","first_gated_state_tick","first_gated_cmd_seq",
        "first_gated_running_time_s","handoff_state_tick","controller_handoff_state_tick","handoff_binary_sha256",
        "duplicate_groups","duplicate_extra_rows","protocol_status","physical_status"]
    write(OUT/"run_summary.csv",[info[r] for r in RUNS],sf)
    write(OUT/"protocol_gates.csv",pg,["run_id","gate","status","detail"])
    valid_excess=len([x for x in excess_median_value.values() if math.isfinite(x)])==len(RUNS)
    er=(max(excess_median_value.values())-min(excess_median_value.values())) if valid_excess else float("nan")
    protocol_ok=all(info[r]["protocol_status"]=="PASS" for r in RUNS)
    physical_ok=all(info[r]["physical_status"]=="PASS" for r in RUNS)
    noearly=alignment_ok and all(not z["first_sustained_divergence_before_40s"] for z in pr)
    endpoint=valid_excess and er<=.010
    if not protocol_ok: label="LOCKSTEP_PROTOCOL_FAIL"
    elif not handoff_ok: label="HANDOFF_STATE_NOT_IDENTICAL"
    elif not physical_ok: label="PHYSICAL_BASELINE_FAIL"
    elif not endpoint or not noearly: label="LOCKSTEP_BASELINE_STILL_NONDETERMINISTIC"
    else: label="READY_FOR_CAUSAL_AB"
    raw=[(run,p.name,sha(p)) for run in RUNS
         for p in sorted((RUN_ROOT/run).iterdir()) if p.is_file()]
    src=["simulate/src/lockstep.h","simulate/src/main.cc",
         "simulate/src/unitree_sdk2_bridge.h","simulate/src/param.h",
         "example/cpp/trot/lockstep_writer_gate.h",
         "example/cpp/trot/lockstep_motion_clock.h",
         "example/cpp/trot/trot_experiment.h",
         "example/cpp/trot/trot_experiment_lifecycle.cpp",
         "example/cpp/trot/trot_experiment_control.cpp",
         "example/cpp/scripts/run_trot.sh",
         "example/cpp/tools/analysis/analyze_phase1_lockstep_premotion_startup.py",
         "example/cpp/configs/phase1_velocity_varying.csv",
         "unitree_robots/go2/scene_leg_lift_demo.xml"]
    commands=[]
    base=("flock /tmp/go2_mujoco_experiment.lock env -u TROT_PD_PULSE_AB "
          "-u TROT_FOUR_THIGH_D90_AB -u TROT_BOUNDED_STANCE_DQ_D4_AB "
          "-u TROT_BOUNDED_STANCE_DQ_AB -u TROT_SEED -u RUN_SEED "
          "SIM_LOCKSTEP=1 TROT_LOCKSTEP_PUBLISH_DIAG=1 "
          "GO2_PROFILE_PATH=example/cpp/configs/phase1_velocity_varying.csv "
          "TROT_CPU_AUTOPIN=1 TROT_DYNAMICS_TOLERANCE_N=20 "
          "TROT_HS_START_PERIOD=0.20 TROT_HS_START_DUTY=0.50 "
          "TROT_HS_SPEED_LEAD=0.25 TROT_HS_ACC_GAIN=10 TROT_HS_ACC_LIMIT=4 "
          "TROT_HS_STEP_CAP=0.52 TROT_HS_SWING_REACH=0.90 "
          "TROT_HS_HYBRID_CONTACT=2 TROT_HS_PITCH_GAIN=24 "
          "TROT_HS_PITCH_DAMP=6 TROT_HS_ROLL_GAIN=20 TROT_HS_ROLL_DAMP=10 "
          "TROT_HS_STABILITY_GOV=1 bash example/cpp/scripts/run_trot.sh 140 "
          "_runs/phase1_lockstep_premotion_startup_20260914/{run} --headless "
          "--wall-clock-motion --controller-duration 86 --wbc-full "
          "--gait-pattern running-trot --kernel raibert-trot --period 0.14 "
          "--duty 0.44 --step-length 0.50 --foot-lift 0.20 --tau-limit 45 "
          "--raibert-velocity-gain 0.010 --raibert-max-adjustment 0.06 "
          "--preview-horizon 4 --support-anchor-feedback "
          "--support-anchor-gain 0.35 --velocity-max-accel 0.80 "
          "--velocity-max-decel 1.20 --velocity-max-jerk 4.0 "
          "--velocity-command-script example/cpp/configs/phase1_velocity_varying.csv "
          "--velocity-max-tracking-lead 0.20 --domain-id {domain}")
    for run,domain in zip(RUNS,(221,222,223)):
        commands.append(base.format(run=run,domain=domain))
    lines=["# Phase1 pre-motion lockstep startup determinism - 2026-09-14","",
      "Hypothesis: deterministic zero-control pre-motion and a frozen handoff before active stand-up remove startup-state/lifecycle divergence from repeated Phase1 baselines.","",
      "Primary label: **%s**."%label,"",
      "Exactly three sequential frozen baselines L1/L2/L3 were executed after Stage 2 passed. D4 and every prior A/B flag were OFF; the inherited Phase1 scene/model/profile/period/duty/WBC-full parameters and fixed CPU affinity were retained. No controller or acceptance threshold was changed.","",
      "## Stage 0 lifecycle audit","",
      "Recorded before Stage 1 behavior edits from the native WSL source inspection.","",
      "- PhysicsThread creates MuJoCo data and calls mj_forward; before the barrier, PhysicsLoop advances through the wall-clock path.",
      "- The bridge DDS readiness check occurs before Go2Bridge construction.",
      "- The controller creates publishers/subscribers, waits for natural settle for wall-clock 0.5 s, then captures start joints and world reference asynchronously.",
      "- The writer thread starts after capture and performs the pre-gate LowCmdWrite(false).",
      "- Before the barrier, RunLockstep delegates to RunWallClock; the first command completes the barrier, after which physics waits for permission and performs one mj_step.",
      "- Before Stage 1, the epoch was tied only to task_.gait_started_; the writer gate engaged afterward.",
      "- Stand-up and gait therefore progressed on the free-running path before the proposed handoff.",
      "- Earliest safe freeze boundary: after mj_forward, run fixed controller-independent zero-control pre-settle, serialize the state, publish nothing until serialization completes, and hold the plant for controller capture.","",
      "Stage 1 used 4000 exact zero-control MuJoCo steps, stable double-state serialization, and writer-gate/motion-clock authority from the pre-motion handoff. Flag-off behavior remains wall-clock.","",
      "## Stage 2","",
      "Passed before launches: simulator test_lockstep and test_lockstep_sim; controller test_lockstep_writer_gate, test_lockstep_motion_clock, and test_lockstep_motion_clock_integration. Focused tests cover frozen first consumption, duplicate suppression, strictly-new ticks, state-tick 0/2 ms timing, and legacy flag-off behavior.","",
      "## Handoff state","",
      "The simulator wrote the post-4000-step state before state publication. handoff_states.csv records stable binary hashes and pairwise maxima for full qpos/qvel plus actuator-derived q/dq; the simulator double state is authoritative.","",
      "|run|steps|sim tick|binary SHA256|controller handoff tick|first gated tick|first gated gait_started|","|---|---:|---:|---|---:|---:|---:|"]
    for x in hr[:3]:
        lines.append("|%s|%s|%s|%s|%s|%s|%s|"%(x["run_id"],x["pre_motion_steps"],x["sim_tick_ms"],x["binary_sha256"],x["controller_handoff_state_tick"],x["controller_first_gated_state_tick"],x["controller_first_gated_gait_started"]))
    lines += ["","Handoff pairwise maxima: qpos=%s, qvel=%s, actuated q=%s, actuated dq=%s; exact binary hashes identical=%s. Required maxima are <=1e-12."%(fmt(mx["qpos"]),fmt(mx["qvel"]),fmt(mx["aq"]),fmt(mx["adq"]),str(exact).lower()),"",
      "## Gates","","protocol_gates.csv records every protocol and handoff gate. The strict post-handoff trace requires 2 ms ticks, zero violations, exact matched-pair trigger, one command update per state tick, no duplicate active LowCmd, and no free/active motion before the handoff. Physical gates are unchanged: active-relative >=40 s, no hard stop before 40 s, continuous-trot in [32,33), excess median [+0.15,+0.35] m/s, and WBC/SRBD/ID medians <0.","",
      "|run|protocol|physical|active-relative s|[32,33) rows|excess median|WBC ax|SRBD ax|ID qdd-x|","|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for run in RUNS:
        x=info[run]
        lines.append("|%s|%s|%s|%s|%s|%s|%s|%s|%s|"%(run,x["protocol_status"],x["physical_status"],x["active_relative_duration_s"],x["window_rows_32_33"],x["excess_median_mps"],x["wbc_desired_ax_median_mps2"],x["srbd_ax_median_mps2"],x["id_qdd_x_median_mps2"]))
    lines += ["","## Trajectory","",
      "Pairwise alignment uses only diag_active_relative_time_s after handoff on a fixed 10 ms grid with maximum nearest tolerance 10 ms; wall-clock timestamps are not truth. pairwise.csv reports p50/p95/max for measured/applied velocity, excess, roll, pitch, physical contact count/mask, controller contact mask, and gait phase. Sustained divergence is measured as registered: measured >0.05 m/s or roll/pitch >2 deg for >=100 ms.","",
      "|pair|grid points|common prefix s|excess p50/p95/max|measured p50/p95/max|roll p50/p95/max deg|pitch p50/p95/max deg|first sustained divergence before 40 s|","|---|---:|---|---|---|---|---|---|"]
    for x in pr:
        lines.append("|%s|%s|%s-%s|%s/%s/%s|%s/%s/%s|%s/%s/%s|%s/%s/%s|%s|"%(x["pair"],x["grid_points"],x["common_active_relative_start_s"],x["common_active_relative_end_s"],x["excess_p50_abs_diff"],x["excess_p95_abs_diff"],x["excess_max_abs_diff"],x["measured_p50_abs_diff"],x["measured_p95_abs_diff"],x["measured_max_abs_diff"],x["roll_p50_abs_diff"],x["roll_p95_abs_diff"],x["roll_max_abs_diff"],x["pitch_p50_abs_diff"],x["pitch_p95_abs_diff"],x["pitch_max_abs_diff"],x["first_sustained_divergence_before_40s"] or "none"))
    lines += ["","Endpoint excess range=%s m/s <=0.010=%s; all protocol=%s, handoff=%s, physical=%s, no sustained divergence before 40 s=%s."%(fmt(er),str(endpoint).lower(),str(protocol_ok).lower(),str(handoff_ok).lower(),str(physical_ok).lower(),str(noearly).lower()), "",
      "## Exact commands and provenance","","The following three commands were run sequentially, with no fourth launch:"]
    lines += commands + ["","Each run_metadata.txt records source HEAD, dirty state, simulator/controller/scene hashes, domain, and argv. Profile SHA256: %s."%info["L1"]["profile_sha256"],"","Raw artifact SHA256 (large raw files remain under _runs):","|run|file|SHA256|","|---|---|---|"]
    lines += ["|%s|%s|%s|"%(x) for x in raw] + ["","Scoped source SHA256:","|path|SHA256|","|---|---|"] + ["|%s|%s|"%(p,sha(ROOT/p)) for p in src] + ["","Derived evidence SHA256:","|file|SHA256|","|---|---|","|handoff_states.csv|%s|"%sha(OUT/"handoff_states.csv"),"|protocol_gates.csv|%s|"%sha(OUT/"protocol_gates.csv"),"|run_summary.csv|%s|"%sha(OUT/"run_summary.csv"),"|pairwise.csv|%s|"%sha(OUT/"pairwise.csv"),"","Checkpoint boundary: exactly three launches and their audit are complete. No fourth launch, D4, A/B intervention, tuning, retry, or follow-up experiment was executed.",""]
    if label=="READY_FOR_CAUSAL_AB":
        lines.append("Recommended next step: execute the separately authorized causal A/B checkpoint from this frozen baseline; not executed here.")
    elif label=="HANDOFF_STATE_NOT_IDENTICAL":
        lines.append("Recommended next step: inspect deterministic handoff serialization in a separately authorized checkpoint; not executed here.")
    elif label=="LOCKSTEP_PROTOCOL_FAIL":
        lines.append("Recommended next step: inspect the failing causal/tick protocol gate in a separately authorized checkpoint; not executed here.")
    elif label=="PHYSICAL_BASELINE_FAIL":
        lines.append("Recommended next step: inspect the inherited physical baseline failure in a separately authorized checkpoint; not executed here.")
    else:
        lines.append("Recommended next step: inspect the remaining lockstep trajectory nondeterminism in a separately authorized verification checkpoint; not executed here.")
    (OUT/"RESULTS.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("label=%s protocol=%s handoff=%s physical=%s endpoint=%s noearly=%s"%(label,protocol_ok,handoff_ok,physical_ok,endpoint,noearly))
    for run in RUNS:
        print(run,"handoff",info[run]["handoff_state_tick"],"first",info[run]["first_gated_state_tick"],"active_end",info[run]["active_relative_duration_s"],"excess",info[run]["excess_median_mps"])
if __name__=="__main__": main()
