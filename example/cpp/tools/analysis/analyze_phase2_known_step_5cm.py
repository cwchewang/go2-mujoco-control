#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,math,re,statistics
from pathlib import Path
LEGS=("fr","fl","rr","rl")
STATUS=("controller_status","safety_status","quality_status","analysis_status","ground_truth_status","dynamics_status","completion_status","manifest_status","lockstep")
def base():
 p=Path(__file__).with_name("analyze_phase1_lockstep_baseline.py")
 s=importlib.util.spec_from_file_location("phase1_baseline",p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def rows(p):
 with p.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def meta(p):
 d={}
 if p.is_file():
  for x in p.read_text(errors="replace").splitlines():
   if "=" in x:k,v=x.split("=",1);d[k]=v
 return d
def n(r,k,d=math.nan):
 try:
  v=float(r.get(k,""));return v if math.isfinite(v) else d
 except:return d
def fl(r,k):return n(r,k,0)>0.5
def med(v):
 v=[x for x in v if math.isfinite(x)];return statistics.median(v) if v else math.nan
def pct(v,q):
 v=sorted(x for x in v if math.isfinite(x))
 if not v:return math.nan
 z=(len(v)-1)*q;i=int(z);j=min(i+1,len(v)-1);return v[i]+(v[j]-v[i])*(z-i)
def fmt(x):return "" if isinstance(x,float) and not math.isfinite(x) else str(x)
def sha(p):
 if not p.is_file():return "MISSING"
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def write(p,rs):
 fs=[]
 for r in rs:
  for k in r:
   if k not in fs:fs.append(k)
 with p.open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=fs,extrasaction="ignore");w.writeheader();w.writerows(rs)
def gate(run,name,ok,detail):return {"run":run,"gate":name,"status":"PASS" if ok else "FAIL","detail":detail}
def active(rs):return [r for r in rs if n(r,"motion_stage",0)==2 and fl(r,"velocity_command_active")]
def hard(p):
 t="".join((p/x).read_text(errors="replace").upper() for x in ("controller.log","simulator.log") if (p/x).is_file())
 return [x for x in ("TROT HARD SAFETY LIMIT REACHED","EMERGENCY_STOP","HARD_SAFETY","SIM_LOCKSTEP_FAIL_CLOSED") if x in t]
def paired(p):
 t=(p/"controller.log").read_text(errors="replace") if (p/"controller.log").is_file() else ""
 m=re.findall(r"PAIRED_HIGHSTATE_SUMMARY\s+cycles=(\d+)\s+validation_failures=(\d+)\s+async_fallbacks=(\d+)",t)
 if not m:return False,{"cycles":"","validation_failures":"MISSING","async_fallbacks":"MISSING"}
 c,f,a=map(int,m[-1]);d={"cycles":c,"validation_failures":f,"async_fallbacks":a};return c>0 and f==0 and a==0,d
def solver(rs):
 q=[r for r in active(rs) if math.isfinite(n(r,"wbc_full_eq_residual"))]
 s=[fl(r,"wbc_full_srbd_ok") and fl(r,"wbc_full_id_ok") for r in q];e=[abs(n(r,"wbc_full_eq_residual")) for r in q]
 d={"valid_rows":len(q),"success_fraction":sum(s)/len(s) if s else math.nan,"eq_residual_p95":pct(e,.95)}
 return bool(q) and all(s) and d["eq_residual_p95"]<=1e-3,d

def a_gate(b,p,rs,md,expected):
 g,pi=b.protocol(p,"A");d=list(g);po,ps=paired(p);d+=[gate("A","paired_highstate",po,str(ps))]
 fv=[n(r,"known_step_feature_enabled") for r in rs];aa=sum(fl(r,"known_step_%s_adaptation_active"%l) for r in rs for l in LEGS)
 d+=[gate("A","adapter_disabled",bool(fv) and all(x==0 for x in fv) and aa==0,"values=%s active=%d"%(sorted(set(fv)),aa))]
 st=all(md.get(k,"") in ("","0","false") for k in STATUS);d+=[gate("A","statuses_zero",st,str({k:md.get(k,"MISSING") for k in STATUS}))]
 hs=hard(p);d+=[gate("A","no_hard_safety",not hs,",".join(hs) or "none")]
 ar=active(rs);x=[n(r,"world_base_x_m") for r in ar];loc=bool(ar) and max(x)>=.60
 d+=[gate("A","active_locomotion_to_pre_step",loc,"rows=%d max_x=%s"%(len(ar),fmt(max(x,default=math.nan))))]
 so,sd=solver(rs);d+=[gate("A","solver_health",so,str(sd))]
 prov=(md.get("git_dirty") in ("false","0","") and md.get("git_head","") and md.get("controller_sha256","") and md.get("simulator_sha256","") and md.get("scene_sha256","") and (not expected or md.get("git_head")==expected))
 d+=[gate("A","source_provenance",bool(prov),"head=%s dirty=%s expected=%s"%(md.get("git_head","MISSING"),md.get("git_dirty","MISSING"),expected or "none"))]
 return all(x["status"]=="PASS" for x in d),d,pi,ps
def first_active(rs):
 for i,r in enumerate(rs):
  if any(fl(r,"known_step_%s_adaptation_active"%l) for l in LEGS):return i
 return len(rs)
def pre(a,b):
 z=first_active(b);aa=a[:z];bb=b[:z];bad=[]
 if len(aa)!=len(bb):bad.append({"row":"COUNT","field":"row_count","a":len(aa),"b":len(bb)})
 keys=[k for k in (aa[0] if aa else {}) if not k.startswith("known_step_") and k in (bb[0] if bb else {})]
 for i,(x,y) in enumerate(zip(aa,bb)):
  for k in keys:
   if x.get(k,"")!=y.get(k,"") and len(bad)<1000:bad.append({"row":i,"field":k,"a":x.get(k,""),"b":y.get(k,"")})
 if not bad:bad=[{"row":"ALL","field":"non_known_step_causal_fields","a":"exact","b":"exact"}]
 return not bad or (len(bad)==1 and bad[0]["field"]=="non_known_step_causal_fields"),z,bad
def isolation(rs):
 cs=[];bad=[];active_count=0;xy=zerr=0.;rises=[];lifts=[]
 d4=("diag_four_thigh_d90_enabled","diag_four_thigh_d90_gate_active","diag_bounded_stance_dq_enabled","diag_bounded_stance_dq_gate_active")
 dv={k:sorted(set(n(r,k) for r in rs if k in r)) for k in d4};cs.append(("d4_off",all(not v or v==[0.] for v in dv.values()),str(dv)))
 cs.append(("feature_enabled",all(fl(r,"known_step_feature_enabled") for r in rs),"all rows enabled"))
 for i,r in enumerate(rs):
  for l in LEGS:
   q="known_step_%s_"%l;act=fl(r,q+"adaptation_active");rise=n(r,q+"rise_m")
   if act:
    active_count+=1;rises.append(rise);lifts.append(n(r,q+"effective_lift_m"))
    if not fl(r,q+"scheduled_swing") or abs(rise)<=1e-9:bad.append("row=%d leg=%s scope"%(i,l))
    fz=n(r,q+"final_target_world_z_m");sz=n(r,q+"swing_start_z_m")
    if math.isfinite(fz) and math.isfinite(sz):zerr=max(zerr,abs(fz-sz-rise))
   nx,ny,fx,fy=[n(r,q+k) for k in ("nominal_touchdown_x_m","nominal_touchdown_y_m","final_target_world_x_m","final_target_world_y_m")]
   if all(math.isfinite(x) for x in (nx,ny,fx,fy)):xy=max(xy,abs(nx-fx),abs(ny-fy))
   h0,h1,fz,nz=n(r,q+"h0_m"),n(r,q+"h1_m"),n(r,q+"final_target_world_z_m"),n(r,q+"nominal_touchdown_z_m")
   if abs(h0-.05)<=1e-7 and abs(h1-.05)<=1e-7 and (abs(h1-h0)>1e-7 or abs(fz-nz)>1e-7):bad.append("row=%d leg=%s accumulation"%(i,l))
 cs.append(("adaptation_scope",not bad,"active=%d errors=%s"%(active_count,";".join(bad[:8]) or "none")))
 cs.append(("nominal_xy_unchanged",xy<=1e-12,"max_error=%g"%xy));cs.append(("final_z_formula",zerr<=1e-9,"max_error=%g"%zerr))
 cs += [("crossing_rise_5cm",all(abs(x-.05)<=1e-7 for x in rises) if rises else True,str(sorted(set(round(x,9) for x in rises)))),("crossing_lift_80mm",all(abs(x-.080)<=1e-7 for x in lifts) if lifts else True,str(sorted(set(round(x,9) for x in lifts))))]
 return all(x[1] for x in cs),cs,{"adaptation_active_samples":active_count,"rise_values_m":sorted(set(round(x,9) for x in rises)),"effective_lift_values_m":sorted(set(round(x,9) for x in lifts)),"max_nominal_xy_error_m":xy,"max_final_z_formula_error_m":zerr}
def dt(rs,i):
 if i+1>=len(rs):return 0.
 a=n(rs[i],"state_tick_s");b=n(rs[i+1],"state_tick_s");return max(0.,b-a) if math.isfinite(a) and math.isfinite(b) else 0.

def cross(rs,x):
 for r in rs:
  if n(r,"world_base_x_m")>=x:return n(r,"state_tick_s")
 return math.nan
def raised(rs):
 out=[]
 for l in LEGS:
  z0=med([n(r,"known_step_%s_actual_z_m"%l) for r in rs if n(r,"world_base_x_m")<.60 and fl(r,"contact_%s"%l.upper())]);q=[]
  for i,r in enumerate(rs):
   if math.isfinite(z0) and fl(r,"contact_%s"%l.upper()) and n(r,"world_base_x_m")>=.80 and n(r,"known_step_%s_actual_x_m"%l)>=.85 and n(r,"known_step_%s_actual_z_m"%l)>=z0+.035:q.append(r)
  tm=sum(dt(rs,i) for i,r in enumerate(rs) if r in q)
  out.append({"leg":l,"floor_reference_z0_m":z0,"first_raised_touchdown_state_tick_s":n(q[0],"state_tick_s") if q else math.nan,"first_raised_touchdown_x_m":n(q[0],"known_step_%s_actual_x_m"%l) if q else math.nan,"first_raised_touchdown_z_m":n(q[0],"known_step_%s_actual_z_m"%l) if q else math.nan,"raised_contact_time_s":tm,"raised_contact_gate":tm>=.10})
 return out
def arm(run,rs,md,p):
 ar=active(rs);x=[n(r,"world_base_x_m") for r in ar];reach=bool(x) and max(x)>=1.45;t=cross(rs,1.45);hold=False
 if math.isfinite(t):hold=bool([r for r in rs if t<=n(r,"state_tick_s")<=t+.5]) and min(n(r,"world_base_x_m") for r in rs if t<=n(r,"state_tick_s")<=t+.5)>=1.35
 win=[r for r in rs if n(r,"world_base_x_m")>=.60 and (not math.isfinite(t) or n(r,"state_tick_s")<=t+.5)]
 roll=[abs(n(r,"imu_roll_rad")) for r in win];pitch=[abs(n(r,"imu_pitch_rad")) for r in win]
 sv=[r for r in ar if math.isfinite(n(r,"wbc_full_eq_residual"))];ok=[fl(r,"wbc_full_srbd_ok") and fl(r,"wbc_full_id_ok") for r in sv];res=[abs(n(r,"wbc_full_eq_residual")) for r in sv]
 status=all(md.get(k,"") in ("","0","false") for k in STATUS);hs=hard(p);td=raised(rs);div=0
 for r in win:
  for l in LEGS:
   if fl(r,"known_step_%s_scheduled_stance"%l):
    e=abs(n(r,"known_step_%s_actual_z_m"%l)-n(r,"known_step_%s_final_target_world_z_m"%l))
    if math.isfinite(e) and e>.12:div+=1
 torque=[abs(n(r,"%s_tau_est"%m)) for r in ar for m in ("FR_hip","FR_thigh","FR_calf","FL_hip","FL_thigh","FL_calf","RR_hip","RR_thigh","RR_calf","RL_hip","RL_thigh","RL_calf")];torque=[x for x in torque if math.isfinite(x)]
 success=reach and hold and all(x["raised_contact_gate"] for x in td) and not hs and status and bool(ok) and all(ok) and bool(res) and pct(res,.95)<=1e-3 and max(roll,default=math.inf)<=.25 and max(pitch,default=math.inf)<=.25 and div<=max(20,len(win)//10)
 d={"run":run,"rows":len(rs),"active_rows":len(ar),"max_base_x_m":max(x,default=math.nan),"first_base_x_080_state_tick_s":cross(rs,.8),"first_base_x_145_state_tick_s":t,"reached_x_145":reach,"stayed_above_x_135_for_050s":hold,"all_legs_raised_contact_010s":all(x["raised_contact_gate"] for x in td),"no_hard_safety":not hs,"statuses_zero":status,"solver_success_fraction":sum(ok)/len(ok) if ok else math.nan,"solver_residual_p95":pct(res,.95),"solver_100pct":bool(ok) and all(ok),"solver_residual_gate":bool(res) and pct(res,.95)<=1e-3,"persistent_command_actual_divergence":div>max(20,len(win)//10),"divergence_rows":div,"max_abs_roll_rad":max(roll,default=math.nan),"p95_abs_roll_rad":pct(roll,.95),"max_abs_pitch_rad":max(pitch,default=math.nan),"p95_abs_pitch_rad":pct(pitch,.95),"p95_abs_base_vertical_velocity_mps":pct([abs(n(r,"world_velocity_z_mps")) for r in ar],.95),"torque_rms_nm":math.sqrt(sum(x*x for x in torque)/len(torque)) if torque else math.nan,"torque_p95_abs_nm":pct(torque,.95),"torque_max_abs_nm":max(torque,default=math.nan),"adapted_samples":sum(fl(r,"known_step_%s_adaptation_active"%l) for r in rs for l in LEGS),"traversal_success":success}
 return d,td

def provenance(root,dirs,mds):
 out=[]
 for run,p in dirs.items():
  for name in ("data.csv","data.csv.id_closure.csv","lockstep_trace.csv","run_metadata.txt","environment.txt","controller.log","simulator.log"):
   q=p/name;out.append({"run":run,"artifact":name,"path":str(q),"bytes":q.stat().st_size if q.is_file() else "MISSING","sha256":sha(q),"git_head":mds[run].get("git_head",""),"git_dirty":mds[run].get("git_dirty",""),"domain_id":mds[run].get("domain_id",""),"simulator_sha256":mds[run].get("simulator_sha256",""),"controller_sha256":mds[run].get("controller_sha256",""),"scene_sha256":mds[run].get("scene_sha256","")})
 for q in (root/"example/cpp/gait/known_step_terrain_adapter.h",root/"example/cpp/gait/cartesian_world_trot.h",root/"example/cpp/trot/trot_experiment_gait.cpp",root/"example/cpp/trot/trot_experiment_diagnostics.cpp",root/"example/cpp/tools/analysis/analyze_phase2_known_step_5cm.py",root/"unitree_robots/go2/scene_known_step_5cm.xml"):
  out.append({"run":"source","artifact":str(q.relative_to(root)),"path":str(q),"bytes":q.stat().st_size if q.is_file() else "MISSING","sha256":sha(q)})
 return out
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--runs-root",type=Path,required=True);ap.add_argument("--output-dir",type=Path,required=True);ap.add_argument("--a-gate-only",action="store_true");ap.add_argument("--expected-head",default="");x=ap.parse_args();root=Path(__file__).resolve().parents[4];rr=x.runs_root.resolve();out=x.output_dir.resolve();out.mkdir(parents=True,exist_ok=True);dirs={"A":rr/"A","B":rr/"B"};bm=base();ar=rows(dirs["A"]/"data.csv");am=meta(dirs["A"]/"run_metadata.txt");ag,agates,api,aps=a_gate(bm,dirs["A"],ar,am,x.expected_head)
 write(out/"protocol_gates.csv",agates);write(out/"a_gate.csv",[{"A_gate_pass":ag,"reasons":";".join(z["gate"] for z in agates if z["status"]=="FAIL"),"paired_summary":json.dumps(aps),"protocol_summary":json.dumps(api)}])
 if x.a_gate_only:print("A_GATE_PASS" if ag else "BASELINE_GATE_FAILED");return 0 if ag else 2
 if not (dirs["B"]/"data.csv").is_file():
  asum,at=arm("A",ar,am,dirs["A"]);bsum={"run":"B","status":"NOT_RUN","traversal_success":False};write(out/"protocol_gates.csv",agates+[gate("B","launch_authorization",False,"A gate failed; B launch prohibited")]);write(out/"preactivation_exact.csv",[{"status":"NOT_RUN","detail":"A gate failed before B authorization"}]);write(out/"adaptation_isolation.csv",[{"gate":"B_not_run","status":"NOT_RUN","detail":"A gate failed before B authorization"}]);write(out/"arm_summary.csv",[asum,bsum]);write(out/"touchdown_summary.csv",at+[{"run":"B","status":"NOT_RUN"}]);write(out/"provenance.csv",provenance(root,dirs,{"A":am,"B":{}}))
  result={"classification":"BASELINE_GATE_FAILED","A_gate_pass":False,"B_gate":False,"preactivation_exact":"NOT_RUN","adaptation_isolation_pass":"NOT_RUN","A_traversal_success":asum["traversal_success"],"B_traversal_success":"NOT_RUN","A":asum,"B":bsum,"A_paired":aps,"source_provenance_ok":True,"launch_count":1,"domains":{"A":am.get("domain_id",""),"B":"NOT_RUN"}}
  (out/"analysis.json").write_text(json.dumps(result,indent=2,sort_keys=True,default=str)+"\n")
  (out/"RESULTS.md").write_text("# Phase2 known-geometry 5 cm step audit\n\nTop-level classification: BASELINE_GATE_FAILED\n\nA gate failed; B was not authorized or launched.\n")
  print("classification=BASELINE_GATE_FAILED A_gate=False B=NOT_RUN");return 0
 br=rows(dirs["B"]/"data.csv");bmeta=meta(dirs["B"]/"run_metadata.txt");bg,bpi=bm.protocol(dirs["B"],"B");bp,bps=paired(dirs["B"]);pex,pn,pr=pre(ar,br);iso,ic,ii=isolation(br)
 write(out/"protocol_gates.csv",agates+bg+[gate("B","paired_highstate",bp,str(bps)),gate("B","preactivation_exact",pex,"rows=%d first_adaptation_index=%d"%(pn,pn))]);write(out/"preactivation_exact.csv",pr);write(out/"adaptation_isolation.csv",[{"gate":k,"status":"PASS" if v else "FAIL","detail":d} for k,v,d in ic])
 asum,at=arm("A",ar,am,dirs["A"]);bsum,bt=arm("B",br,bmeta,dirs["B"]);write(out/"arm_summary.csv",[asum,bsum]);write(out/"touchdown_summary.csv",at+bt);write(out/"provenance.csv",provenance(root,dirs,{"A":am,"B":bmeta}))
 samehead=am.get("git_head","")==bmeta.get("git_head","")!="";samebin=all(am.get(k,"")==bmeta.get(k,"")!="" for k in ("simulator_sha256","controller_sha256","scene_sha256"));source=samehead and samebin and am.get("git_dirty")=="false" and bmeta.get("git_dirty")=="false";prot=ag and api.get("protocol_status")=="PASS" and bpi.get("protocol_status")=="PASS" and bp and source;bstatus=all(bmeta.get(k,"") in ("","0","false") for k in STATUS);asuc=asum["traversal_success"];bsuc=bsum["traversal_success"]
 if not ag:cl="BASELINE_GATE_FAILED"
 elif not prot or not iso or not bstatus:cl="PROTOCOL_FAILURE"
 elif not pex:cl="INCONCLUSIVE_PREACTIVATION_DIVERGENCE"
 elif bsuc and not asuc:cl="SUPPORTED_ENABLES_TRAVERSAL"
 elif asuc and bsuc:cl="SUPPORTED_SAFE_TRAVERSAL_BASELINE_ALSO_PASSES"
 elif asuc and not bsuc:cl="ADAPTATION_HARMFUL"
 else:cl="ADAPTATION_FAILED"
 result={"classification":cl,"A_gate_pass":ag,"B_gate":prot and iso and bstatus,"preactivation_exact":pex,"preactivation_rows":pn,"adaptation_isolation_pass":iso,"A_traversal_success":asuc,"B_traversal_success":bsuc,"A":asum,"B":bsum,"isolation":ii,"A_paired":aps,"B_paired":bps,"source_provenance_ok":source,"launch_count":2,"domains":{"A":am.get("domain_id",""),"B":bmeta.get("domain_id","")}}
 (out/"analysis.json").write_text(json.dumps(result,indent=2,sort_keys=True,default=str)+"\n")
 (out/"RESULTS.md").write_text("# Phase2 known-geometry 5 cm step audit\n\nTop-level classification: %s\n\nA gate: %s; exact pre-activation comparison: %s; B isolation: %s.\n\nA traversal: %s; B traversal: %s.\n"%(cl,"PASS" if ag else "FAIL","PASS" if pex else "FAIL","PASS" if iso else "FAIL","PASS" if asuc else "FAIL","PASS" if bsuc else "FAIL"))
 print("classification=%s A_gate=%s preactivation=%s isolation=%s"%(cl,ag,pex,iso));return 0
if __name__=="__main__":raise SystemExit(main())
