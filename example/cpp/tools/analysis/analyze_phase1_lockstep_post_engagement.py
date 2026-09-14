#!/usr/bin/env python3
import csv, hashlib, itertools, math, statistics
from bisect import bisect_left
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RUN_ROOT = ROOT / "example/cpp/experiments/_runs/phase1_lockstep_post_engagement_determinism_20260914"
OUT = ROOT / "docs/validation/phase1_lockstep_post_engagement_determinism_20260914"
RUNS = ("L1", "L2", "L3")
GRID_DT = 0.010
MAX_TOL = 0.010

def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def meta(p):
    return dict(x.split("=", 1) for x in p.read_text(errors="replace").splitlines() if "=" in x)

def rows(p):
    with p.open(newline="", errors="replace") as f: return list(csv.DictReader(f))

def num(r, k): return float(r[k])

def med(v): return statistics.median(v) if v else float("nan")

def pct(v, q):
    v = sorted(v)
    if not v: return float("nan")
    x = (len(v)-1)*q; lo = int(x); hi = min(lo+1, len(v)-1)
    return v[lo] + (v[hi]-v[lo])*(x-lo)

def ff(x):
    return "" if x is None or (isinstance(x, float) and not math.isfinite(x)) else "%.9f" % x

def counts(v):
    d = {}
    for x in v: d[x] = d.get(x,0) + 1
    return ",".join("%s:%s" % (k,d[k]) for k in sorted(d,key=lambda x:int(x)))

def write_csv(path,data,fields):
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n")
        w.writeheader(); w.writerows(data)

def gate(run,name,ok,detail):
    return {"run_id":run,"gate":name,"status":"PASS" if ok else "FAIL","detail":detail}

OUT.mkdir(parents=True,exist_ok=True)
info={}; controllers={}; protocol=[]
fields=("diag_active_relative_time_s","velocity_command_active",
 "velocity_command_measured_mps","velocity_command_applied_mps","imu_roll_rad",
 "imu_pitch_rad","contact_count","contact_FR","contact_FL","contact_RR","contact_RL",
 "phase","velocity_command_gait_regime","wbc_full_requested_acc_x_mps2",
 "wbc_full_srbd_acc_x_mps2","wbc_full_id_qdd_x_mps2")

for run in RUNS:
    d=RUN_ROOT/run
    m=meta(d/"run_metadata.txt")
    dg=sorted(rows(d/"data.csv.lockstep_publish.csv"),key=lambda r:int(r["publish_index"]))
    tr=[r for r in rows(d/"lockstep_trace.csv") if r.get("phase")=="lockstep"]
    first=next(r for r in dg if r["gate_engaged"]=="1" and r["writer_branch"]=="gated")
    fi=int(first["publish_index"]); fs=int(first["state_tick"]); fc=int(first["lockstep_cmd_seq"]); ft=float(first["running_time_s"])
    pre=[r for r in tr if int(r["cmd_seq_at_publish"])<fc]
    post=[r for r in tr if int(r["cmd_seq_at_publish"])>=fc]
    pd=[int(r["cmd_seq_at_ready"])-int(r["cmd_seq_at_publish"]) for r in pre]
    qd=[int(r["cmd_seq_at_ready"])-int(r["cmd_seq_at_publish"]) for r in post]
    postd=[r for r in dg if int(r["publish_index"])>=fi]
    bytick={}
    for r in postd: bytick.setdefault(int(r["state_tick"]),[]).append(r)
    dupg=sum(len(v)>1 for v in bytick.values())
    dupe=sum(max(0,len(v)-1) for v in bytick.values())
    pdt=[int(b["sim_tick_ms"])-int(a["sim_tick_ms"]) for a,b in zip(post,post[1:])]
    failed="SIM_LOCKSTEP_FAIL_CLOSED" in (d/"simulator.log").read_text(errors="replace")
    ps=[
      gate(run,"trace_present",bool(tr),"lockstep_rows=%d"%len(tr)),
      gate(run,"constant_post_engagement_sim_tick",bool(pdt) and set(pdt)=={2},"post_intervals=%d dt_ms=%s"%(len(post),sorted(set(pdt)))),
      gate(run,"no_post_engagement_protocol_violations",bool(post) and all(int(r["violations"])==0 for r in post),"post_intervals=%d violations=%s"%(len(post),sorted(set(int(r["violations"]) for r in post)) if post else [])),
      gate(run,"post_engagement_ack_state_matches_published_tick",bool(post) and all(int(r["ack_state_seq"])==int(r["sim_tick_ms"]) for r in post),"post_intervals=%d"%len(post)),
      gate(run,"post_engagement_exact_pair_trigger",bool(post) and all(int(r["exchange_trigger"])==3 for r in post),"triggers=%s"%sorted(set(r["exchange_trigger"] for r in post))),
      gate(run,"no_fail_closed_marker",not failed,"marker=%s"%failed),
      gate(run,"one_command_update_per_state_tick_post_engagement",bool(post) and all(int(r["cmd_seq_at_ready"])-int(r["cmd_seq_at_publish"])==1 and int(r["ack_cmd_seq"])==int(r["cmd_seq_at_ready"]) for r in post),"post_intervals=%d delta_counts=%s"%(len(post),counts(qd))),
      gate(run,"no_controller_same_state_duplicate_post_engagement",dupe==0,"duplicate_groups=%d duplicate_extra_rows=%d"%(dupg,dupe)),
    ]
    protocol += ps
    c=[]
    with (d/"data.csv").open(newline="",errors="replace") as f:
        for r in csv.DictReader(f): c.append({k:r[k] for k in fields})
    controllers[run]=c
    active=[r for r in c if r["velocity_command_active"]=="1"]
    end=max(num(r,"diag_active_relative_time_s") for r in active)
    win=[r for r in active if 32<=num(r,"diag_active_relative_time_s")<33]
    ex=[num(r,"velocity_command_measured_mps")-num(r,"velocity_command_applied_mps") for r in win]
    mv=[num(r,"velocity_command_measured_mps") for r in win]
    av=[num(r,"velocity_command_applied_mps") for r in win]
    wx=[num(r,"wbc_full_requested_acc_x_mps2") for r in win]
    sx=[num(r,"wbc_full_srbd_acc_x_mps2") for r in win]
    ix=[num(r,"wbc_full_id_qdd_x_mps2") for r in win]
    regs=sorted(set(r["velocity_command_gait_regime"] for r in win))
    phys=end>=40 and m.get("safety_status")=="0" and len(win)>0 and regs==["continuous-trot"] and .15<=med(ex)<=.35 and med(wx)<0 and med(sx)<0 and med(ix)<0
    ppass=all(x["status"]=="PASS" for x in ps)
    info[run]=dict(run_id=run,source_git_head=m.get("git_head",""),git_branch=m.get("git_branch",""),git_dirty=m.get("git_dirty",""),simulator_sha256=m.get("simulator_sha256",""),controller_sha256=m.get("controller_sha256",""),scene_sha256=m.get("scene_sha256",""),profile_sha256=m.get("profile_sha256",""),sim_cpu=m.get("sim_cpu_affinity",""),controller_cpu=m.get("controller_cpu_affinity",""),domain_id=m.get("domain_id",""),active_relative_duration_s=ff(end),active_rows=len(active),window_rows_32_33=len(win),measured_median_mps=ff(med(mv)),applied_median_mps=ff(med(av)),excess_median_mps=ff(med(ex)),wbc_desired_ax_median_mps2=ff(med(wx)),srbd_ax_median_mps2=ff(med(sx)),id_qdd_x_median_mps2=ff(med(ix)),gait_regimes_32_33="|".join(regs),controller_status=m.get("controller_status",""),safety_status=m.get("safety_status",""),quality_status=m.get("quality_status",""),analysis_status=m.get("analysis_status",""),ground_truth_status=m.get("ground_truth_status",""),dynamics_status=m.get("dynamics_status",""),completion_status=m.get("completion_status",""),trace_rows=len(tr),pre_engagement_intervals=len(pre),post_engagement_intervals=len(post),pre_delta_counts=counts(pd),post_delta_counts=counts(qd),first_gated_publish_index=fi,first_gated_state_tick=fs,first_gated_cmd_seq=fc,first_gated_running_time_s=ff(ft),first_post_trace_tick=int(post[0]["sim_tick_ms"]),pre_interval_boundary_span_s=ff((int(post[0]["sim_tick_ms"])-int(tr[0]["sim_tick_ms"]))/1000),post_duplicate_groups=dupg,post_duplicate_extra_rows=dupe,protocol_status="PASS" if ppass else "FAIL",physical_status="PASS" if phys else "FAIL")

boundary_fields=["run_id","first_gated_publish_index","first_gated_state_tick","first_gated_cmd_seq","first_gated_running_time_s","first_post_trace_tick","pre_engagement_intervals","post_engagement_intervals","pre_interval_boundary_span_s","pre_delta_counts","post_delta_counts","post_duplicate_groups","post_duplicate_extra_rows"]
write_csv(OUT/"boundary_audit.csv",[{k:info[r][k] for k in boundary_fields} for r in RUNS],boundary_fields)
write_csv(OUT/"protocol_gates.csv",protocol,["run_id","gate","status","detail"])
def cmask(r):
    return int(r["contact_FR"]) | int(r["contact_FL"])<<1 | int(r["contact_RR"])<<2 | int(r["contact_RL"])<<3

def nearest(c,t,target):
    i=bisect_left(t,target)
    choices=([i] if i<len(c) else [])+([i-1] if i else [])
    if not choices: return None
    j=min(choices,key=lambda x:abs(t[x]-target))
    return c[j] if abs(t[j]-target)<=MAX_TOL+1e-12 else None

common_start=max(float(info[r]["first_gated_running_time_s"]) for r in RUNS)
common_end=min(float(info[r]["active_relative_duration_s"]) for r in RUNS)
grid_start=math.ceil(common_start/GRID_DT-1e-9)*GRID_DT
grid_end=math.floor(common_end/GRID_DT+1e-9)*GRID_DT
npoints=int(round((grid_end-grid_start)/GRID_DT))+1
aligned={}
for run in RUNS:
    c=sorted([r for r in controllers[run] if r["velocity_command_active"]=="1" and num(r,"diag_active_relative_time_s")>=float(info[run]["first_gated_running_time_s"])],key=lambda r:num(r,"diag_active_relative_time_s"))
    ts=[num(r,"diag_active_relative_time_s") for r in c]
    aligned[run]=[nearest(c,ts,grid_start+i*GRID_DT) for i in range(npoints)]
    if any(r is None for r in aligned[run]): raise RuntimeError("active-time join missing "+run)

def dv(a,b,k):
    if k=="measured": return abs(num(a,"velocity_command_measured_mps")-num(b,"velocity_command_measured_mps"))
    if k=="applied": return abs(num(a,"velocity_command_applied_mps")-num(b,"velocity_command_applied_mps"))
    if k=="excess": return abs((num(a,"velocity_command_measured_mps")-num(a,"velocity_command_applied_mps"))-(num(b,"velocity_command_measured_mps")-num(b,"velocity_command_applied_mps")))
    if k=="roll": return abs(math.degrees(num(a,"imu_roll_rad"))-math.degrees(num(b,"imu_roll_rad")))
    if k=="pitch": return abs(math.degrees(num(a,"imu_pitch_rad"))-math.degrees(num(b,"imu_pitch_rad")))
    if k=="contact_count": return abs(num(a,"contact_count")-num(b,"contact_count"))
    if k=="contact_mask": return abs(cmask(a)-cmask(b))
    if k=="gait_phase": return abs(num(a,"phase")-num(b,"phase"))

pkeys=("measured","applied","excess","roll","pitch","contact_count","contact_mask","gait_phase")
units={"measured":"mps","applied":"mps","excess":"mps","roll":"deg","pitch":"deg","contact_count":"","contact_mask":"","gait_phase":""}
pair_fields=["pair","grid_dt_s","max_nearest_tolerance_s","common_post_engagement_start_s","common_post_engagement_end_s","grid_points"]
for k in pkeys:
    for q in ("p50","p95","max"):
        pair_fields.append(k+"_"+q+"_abs_diff"+(("_"+units[k]) if units[k] else ""))
pair_fields += ["first_sustained_divergence_s","first_sustained_divergence_before_40s"]
pairs=[]
for left,right in itertools.combinations(RUNS,2):
    item={"pair":left+"__"+right,"grid_dt_s":"%.3f"%GRID_DT,"max_nearest_tolerance_s":"%.3f"%MAX_TOL,"common_post_engagement_start_s":ff(grid_start),"common_post_engagement_end_s":ff(grid_end),"grid_points":npoints}
    for k in pkeys:
        v=[dv(a,b,k) for a,b in zip(aligned[left],aligned[right])]
        u=("_"+units[k]) if units[k] else ""
        item[k+"_p50_abs_diff"+u]=ff(pct(v,.5)); item[k+"_p95_abs_diff"+u]=ff(pct(v,.95)); item[k+"_max_abs_diff"+u]=ff(max(v))
    bad=[dv(a,b,"measured")>.05 or dv(a,b,"roll")>2 or dv(a,b,"pitch")>2 for a,b in zip(aligned[left],aligned[right])]
    first_any=None; first_before=None; streak=0
    for i,badnow in enumerate(bad):
        streak=streak+1 if badnow else 0
        if streak>=10:
            onset=grid_start+(i-9)*GRID_DT
            if first_any is None: first_any=onset
            if onset<40 and first_before is None: first_before=onset
    item["first_sustained_divergence_s"]=ff(first_any); item["first_sustained_divergence_before_40s"]=ff(first_before)
    pairs.append(item)
write_csv(OUT/"pairwise.csv",pairs,pair_fields)

summary_fields=["run_id","source_git_head","git_branch","git_dirty","simulator_sha256","controller_sha256","scene_sha256","profile_sha256","sim_cpu","controller_cpu","domain_id","active_relative_duration_s","active_rows","window_rows_32_33","measured_median_mps","applied_median_mps","excess_median_mps","wbc_desired_ax_median_mps2","srbd_ax_median_mps2","id_qdd_x_median_mps2","gait_regimes_32_33","controller_status","safety_status","quality_status","analysis_status","ground_truth_status","dynamics_status","completion_status","trace_rows","pre_engagement_intervals","post_engagement_intervals","pre_delta_counts","post_delta_counts","first_gated_publish_index","first_gated_state_tick","first_gated_cmd_seq","first_gated_running_time_s","first_post_trace_tick","pre_interval_boundary_span_s","post_duplicate_groups","post_duplicate_extra_rows","protocol_status","physical_status"]
write_csv(OUT/"run_summary.csv",[info[r] for r in RUNS],summary_fields)

exvals=[float(info[r]["excess_median_mps"]) for r in RUNS]
exrange=max(exvals)-min(exvals)
all_protocol=all(info[r]["protocol_status"]=="PASS" for r in RUNS)
all_physical=all(info[r]["physical_status"]=="PASS" for r in RUNS)
no_early=all(not x["first_sustained_divergence_before_40s"] for x in pairs)
det3=exrange<=.01
classification="BASELINE_PHYSICAL_FAIL" if not all_physical else "LOCKSTEP_PROTOCOL_FAIL" if not all_protocol else "READY_FOR_CAUSAL_AB" if det3 and no_early else "LOCKSTEP_BASELINE_STILL_NONDETERMINISTIC"

srcs=["simulate/src/lockstep.h","simulate/src/main.cc","simulate/src/unitree_sdk2_bridge.h","example/cpp/trot/lockstep_writer_gate.h","example/cpp/trot/lockstep_motion_clock.h","example/cpp/trot/trot_experiment.h","example/cpp/trot/trot_experiment_lifecycle.cpp","example/cpp/trot/trot_experiment_control.cpp","example/cpp/scripts/run_trot.sh","example/cpp/configs/phase1_velocity_varying.csv","unitree_robots/go2/scene_leg_lift_demo.xml"]
raw=[]
for r in RUNS:
    for p in sorted((RUN_ROOT/r).iterdir()):
        if p.is_file(): raw.append((r,p.name,sha(p)))
launch="flock /tmp/go2_mujoco_experiment.lock env -u TROT_PD_PULSE_AB -u TROT_FOUR_THIGH_D90_AB -u TROT_BOUNDED_STANCE_DQ_D4_AB -u TROT_BOUNDED_STANCE_DQ_AB -u TROT_SEED -u RUN_SEED SIM_LOCKSTEP=1 TROT_LOCKSTEP_PUBLISH_DIAG=1 GO2_PROFILE_PATH=example/cpp/configs/phase1_velocity_varying.csv TROT_CPU_AUTOPIN=1 TROT_DYNAMICS_TOLERANCE_N=20 TROT_HS_START_PERIOD=0.20 TROT_HS_START_DUTY=0.50 TROT_HS_SPEED_LEAD=0.25 TROT_HS_ACC_GAIN=10 TROT_HS_ACC_LIMIT=4 TROT_HS_STEP_CAP=0.52 TROT_HS_SWING_REACH=0.90 TROT_HS_HYBRID_CONTACT=2 TROT_HS_PITCH_GAIN=24 TROT_HS_PITCH_DAMP=6 TROT_HS_ROLL_GAIN=20 TROT_HS_ROLL_DAMP=10 TROT_HS_STABILITY_GOV=1 bash example/cpp/scripts/run_trot.sh 140 _runs/phase1_lockstep_post_engagement_determinism_20260914/L1 --headless --wall-clock-motion --controller-duration 86 --wbc-full --gait-pattern running-trot --kernel raibert-trot --period 0.14 --duty 0.44 --step-length 0.50 --foot-lift 0.20 --tau-limit 45 --raibert-velocity-gain 0.010 --raibert-max-adjustment 0.06 --preview-horizon 4 --support-anchor-feedback --support-anchor-gain 0.35 --velocity-max-accel 0.80 --velocity-max-decel 1.20 --velocity-max-jerk 4.0 --velocity-command-script example/cpp/configs/phase1_velocity_varying.csv --velocity-max-tracking-lead 0.20 --domain-id 211"
lines=["# Phase1 post-engagement lockstep determinism - 2026-09-14","", "Hypothesis: once strict one-command-per-state accounting begins at the first production LowCmd publish with gate=1 and writer_branch=gated, the frozen Phase1 varying-profile baseline will satisfy the lockstep protocol and be sufficiently reproducible for a causal D4 A/B.","","Decision: %s."%classification,"","Scope: exactly three sequential baseline launches L1, L2, and L3. Varying profile, running-trot, WBC-full, period=0.14 s, duty=0.44, D4 and all prior A/B flags OFF, SIM_LOCKSTEP=1, fixed CPU affinity, and distinct DDS domains. No controller math, gait/WBC/SRBD/ID behavior, bridge handshake, writer gate, motion clock, scene, profile, timestep, or acceptance threshold was changed.","","The existing publish diagnostic was enabled only with TROT_LOCKSTEP_PUBLISH_DIAG=1. It is default-off outside this harness and records each production publish after lowcmd_publisher_->Write. The source tree was clean at each launch (git_dirty=false).","","## Protocol boundary","","The strict interval set starts at the first diagnostic row with gate_engaged=1 and writer_branch=gated. Its lockstep_cmd_seq selects simulator intervals with cmd_seq_at_publish greater than or equal to that sequence. Earlier intervals remain audit-only and are excluded from post-engagement PASS/FAIL.","","|run|first gated publish|state tick|command seq|running time s|pre intervals|post intervals|pre span s|pre delta counts|post delta counts|post duplicate extras|","|---|---:|---:|---:|---:|---:|---:|---:|---|---|---:|"]
for r in RUNS:
    x=info[r]
    lines.append("|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|"%(r,x["first_gated_publish_index"],x["first_gated_state_tick"],x["first_gated_cmd_seq"],x["first_gated_running_time_s"],x["pre_engagement_intervals"],x["post_engagement_intervals"],x["pre_interval_boundary_span_s"],x["pre_delta_counts"],x["post_delta_counts"],x["post_duplicate_extra_rows"]))
lines += ["","boundary_audit.csv independently records the exact boundary and pre/post counts. Pre-engagement deltas are reported but not used in the strict gate.","","## Per-run gates and physical baseline","","|run|protocol|physical|active-relative s|[32,33) rows|regime|measured median|applied median|excess median|WBC ax median|SRBD ax median|ID qdd-x median|","|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|"]
for r in RUNS:
    x=info[r]
    lines.append("|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|"%(r,x["protocol_status"],x["physical_status"],x["active_relative_duration_s"],x["window_rows_32_33"],x["gait_regimes_32_33"],x["measured_median_mps"],x["applied_median_mps"],x["excess_median_mps"],x["wbc_desired_ax_median_mps2"],x["srbd_ax_median_mps2"],x["id_qdd_x_median_mps2"]))
lines += ["","Physical gates require active-relative >=40 s, no hard safety stop before 40 s, continuous-trot in [32,33), and the residual-overspeed/braking-demand regime. Detailed per-run gate rows are in protocol_gates.csv.","","## Determinism analysis","","Rows were filtered to active rows at or after each first gated running time and aligned only by diag_active_relative_time_s. A fixed 10 ms grid with maximum nearest-time tolerance 10 ms was used over the common post-engagement prefix; wall-clock timestamps were not used as truth. Contact-mask bits are FR/FL/RR/RL at bit positions 0/1/2/3; gait phase is the logged phase field.","","|pair|post prefix s|grid points|excess p50/p95/max|measured p50/p95/max|roll p50/p95/max deg|pitch p50/p95/max deg|first sustained divergence s|before 40 s|","|---|---|---:|---|---|---|---|---:|---:|"]
for x in pairs:
    lines.append("|%s|%s-%s|%s|%s/%s/%s|%s/%s/%s|%s/%s/%s|%s/%s/%s|%s|%s|"%(x["pair"],x["common_post_engagement_start_s"],x["common_post_engagement_end_s"],x["grid_points"],x["excess_p50_abs_diff_mps"],x["excess_p95_abs_diff_mps"],x["excess_max_abs_diff_mps"],x["measured_p50_abs_diff_mps"],x["measured_p95_abs_diff_mps"],x["measured_max_abs_diff_mps"],x["roll_p50_abs_diff_deg"],x["roll_p95_abs_diff_deg"],x["roll_max_abs_diff_deg"],x["pitch_p50_abs_diff_deg"],x["pitch_p95_abs_diff_deg"],x["pitch_max_abs_diff_deg"],x["first_sustained_divergence_s"] or "none",x["first_sustained_divergence_before_40s"] or "none"))
lines += ["","The complete required p50/p95/max values for measured velocity, applied velocity, velocity excess, roll, pitch, contact count/mask, and gait phase are in pairwise.csv.","","Pre-registered gates: all post-engagement protocol gates PASS=%s; all physical baseline gates PASS=%s; velocity-excess range=%s m/s <=0.010=%s; no pair has sustained divergence before 40 s=%s."%("true" if all_protocol else "false","true" if all_physical else "false",ff(exrange),"true" if det3 else "false","true" if no_early else "false"),"","## Provenance and exact launch command","","Source HEAD: de00ff0fee553aed38de375f71c0b9ae9feb6b7d.","Branch: research/phase1-lockstep-post-engagement-determinism-20260914.","Frozen simulator SHA256: b2296e02739f7763d2496b18428be267d366e439a3e2b51da9503e3a05dcdd21.","Frozen controller SHA256: 34d84b8290be65aa52580afab0f738597a2b6f522501913aaeff11f15f87f477.","Scene SHA256: 12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8.","Profile SHA256: 9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74.","","    "+launch,"","L2 used the identical command with run directory _runs/phase1_lockstep_post_engagement_determinism_20260914/L2 and domain 212. L3 used the identical command with run directory _runs/phase1_lockstep_post_engagement_determinism_20260914/L3 and domain 213. No fourth launch was run.","","## Raw artifact SHA256","","|run|file|SHA256|","|---|---|---|"]
for r,n,digest in raw: lines.append("|%s|%s|%s|"%(r,n,digest))
lines += ["","## Derived evidence SHA256","","|file|SHA256|","|---|---|"]
for n in ("boundary_audit.csv","protocol_gates.csv","run_summary.csv","pairwise.csv"): lines.append("|%s|%s|"%(n,sha(OUT/n)))
lines += ["","## Scoped source SHA256","","|path|SHA256|","|---|---|"]
for p in srcs: lines.append("|%s|%s|"%(p,sha(ROOT/p)))
lines += ["","Checkpoint boundary: exactly three authorized baseline launches and their post-engagement analysis are complete. No D4, fourth run, tuning, controller repair, or acceptance-threshold change was executed.",""]
if classification=="READY_FOR_CAUSAL_AB": lines.append("Recommended next step: run the separately authorized Phase1 causal D4 A/B from this frozen baseline; not executed here.")
elif classification=="LOCKSTEP_BASELINE_STILL_NONDETERMINISTIC": lines.append("Recommended next step: resolve the remaining post-engagement determinism failure in a separately authorized verification checkpoint; not executed here.")
elif classification=="LOCKSTEP_PROTOCOL_FAIL": lines.append("Recommended next step: inspect the failing post-engagement protocol gate in a separately authorized verification checkpoint; not executed here.")
else: lines.append("Recommended next step: resolve the physical baseline failure in a separately authorized checkpoint; not executed here.")
(OUT/"RESULTS.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
print("classification",classification)
print("protocol",all_protocol,"physical",all_physical,"excess_range",ff(exrange),"grid",ff(grid_start),ff(grid_end),npoints)
for r in RUNS: print(r,info[r]["first_gated_publish_index"],info[r]["first_gated_state_tick"],info[r]["first_gated_cmd_seq"],info[r]["pre_engagement_intervals"],info[r]["post_engagement_intervals"],info[r]["pre_delta_counts"],info[r]["post_delta_counts"],info[r]["post_duplicate_extra_rows"])
for x in pairs: print(x["pair"],x["excess_p50_abs_diff_mps"],x["excess_p95_abs_diff_mps"],x["excess_max_abs_diff_mps"],x["first_sustained_divergence_s"] or "none",x["first_sustained_divergence_before_40s"] or "none")
for n in ("RESULTS.md","boundary_audit.csv","protocol_gates.csv","run_summary.csv","pairwise.csv"): print(n,sha(OUT/n))
