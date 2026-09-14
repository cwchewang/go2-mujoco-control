#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,math,re,statistics,sys
from pathlib import Path

ACTIVE="diag_bounded_stance_dq_active_relative_time_s"
WINDOWS={"pre":(31.9,32.1),"early":(32.1,33.0),"middle":(33.0,36.0),"late":(36.0,39.9),"full":(32.1,39.9)}
STATUS=("controller_status","safety_status","quality_status","analysis_status","ground_truth_status","dynamics_status","completion_status")
PAIR_RE=re.compile(r"PAIRED_HIGHSTATE_SUMMARY\s+cycles=(\d+)\s+validation_failures=(\d+)\s+async_fallbacks=(\d+)")

def loadmod(path,name):
 s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); sys.modules[name]=m; s.loader.exec_module(m); return m

def read(path):
 with path.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))

def write(path,rows):
 fields=[]
 for r in rows:
  for k in r:
   if k not in fields:fields.append(k)
 with path.open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)

def num(r,k,d=math.nan):
 try:return float(r.get(k,""))
 except:return d

def med(xs):
 xs=[x for x in xs if math.isfinite(x)];return statistics.median(xs) if xs else math.nan

def q(xs,p):
 xs=sorted(x for x in xs if math.isfinite(x))
 if not xs:return math.nan
 z=(len(xs)-1)*p;i=int(z);j=min(i+1,len(xs)-1);return xs[i]+(xs[j]-xs[i])*(z-i)

def window(rows,a,b):return [r for r in rows if a<=num(r,ACTIVE)<b]

def paired(run):
 p=run/"controller.log";t=p.read_text(errors="replace") if p.exists() else "";m=list(PAIR_RE.finditer(t))
 if not m:return False,{"cycles":0,"validation_failures":"missing","async_fallbacks":"missing"}
 x=m[-1];d={"cycles":int(x.group(1)),"validation_failures":x.group(2),"async_fallbacks":x.group(3)}
 return d["cycles"]>0 and d["validation_failures"]=="0" and d["async_fallbacks"]=="0",d

def hard(run):
 p=run/"controller.log";t=p.read_text(errors="replace") if p.exists() else ""
 return "Trot hard safety limit reached" in t or "EMERGENCY_STOP" in t

def a_gate(base,run,rows,meta):
 gates,summary=base.protocol(run,"A");pok,pinfo=paired(run);why=[]
 if summary["protocol_status"]!="PASS":why.append("protocol")
 if not pok:why.append("paired_highstate")
 for k in STATUS:
  if meta.get(k,"") not in ("","0"):why.append(f"{k}={meta.get(k)}")
 ts=[num(r,ACTIVE) for r in rows if math.isfinite(num(r,ACTIVE))]
 if not ts or max(ts)<40:why.append("active<40")
 if any(r.get("motion_stage")!="2" for r in window(rows,32,40)):why.append("not_locomotion")
 g=window(rows,32,33);ex=med([num(r,"velocity_command_measured_mps")-num(r,"velocity_command_applied_mps") for r in g])
 if not .15<=ex<=.35:why.append(f"excess={ex}")
 for k in ("wbc_full_requested_acc_x_mps2","wbc_full_srbd_acc_x_mps2","wbc_full_id_qdd_x_mps2"):
  v=med([num(r,k) for r in g])
  if not math.isfinite(v) or v>=0:why.append(f"{k}={v}")
 if hard(run):why.append("hard_safety")
 return not why,why,gates,pinfo,ex

def causal_fields(row):
 fixed=("cmd_time_s","state_tick_s","motion_dt_s","motion_stage","cycle_index","phase","velocity_command_requested_mps","velocity_command_shaped_mps","velocity_command_applied_mps","velocity_command_measured_mps","body_velocity_x_mps","world_velocity_x_mps","imu_gyro_x_radps","imu_gyro_y_radps","imu_gyro_z_radps","imu_roll_rad","imu_pitch_rad","imu_yaw_rad","wbc_shadow_contact_mask","contact_count","wbc_full_requested_acc_x_mps2","wbc_full_srbd_acc_x_mps2","wbc_full_id_qdd_x_mps2")
 suff=("_q_target","_dq_target","_kp","_kd","_tau_ff","_q_state","_dq_state")
 return [k for k in fixed if k in row]+sorted(k for k in row if k.startswith(("FR_","FL_","RR_","RL_")) and k.endswith(suff))

def pre_exact(a,b):
 aa=window(a,31.9,32.1);bb=window(b,31.9,32.1);out=[]
 if len(aa)!=len(bb):return False,[{"field":"row_count","a":len(aa),"b":len(bb)}]
 if not aa:return False,[{"field":"row_count","a":0,"b":0}]
 fields=causal_fields(aa[0]);ok=True
 for i,(x,y) in enumerate(zip(aa,bb)):
  if x.get(ACTIVE)!=y.get(ACTIVE):ok=False;out.append({"row":i,"field":ACTIVE,"a":x.get(ACTIVE),"b":y.get(ACTIVE)})
  for k in fields:
   if x.get(k)!=y.get(k):
    ok=False
    if len(out)<300:out.append({"row":i,"field":k,"a":x.get(k),"b":y.get(k)})
 if ok:out=[{"row":"all","field":"ALL_CAUSAL_FIELDS","a":"exact","b":"exact"}]
 return ok,out

def isolation(a,b):
 p="diag_bounded_stance_dq_";mot=sorted(k[len(p):-12] for k in b[0] if k.startswith(p) and k.endswith("_baseline_dq"));legs=sorted(set(x.split("_",1)[0] for x in mot));issues=[];changed=0;mxq=mxd=0.;inv=fb=0
 for i,r in enumerate(a):
  for m in mot:
   if r.get(p+m+"_baseline_dq")!=r.get(p+m+"_applied_dq"):issues.append(f"A correction row {i} {m}");break
  if issues:break
 for i,r in enumerate(b):
  t=num(r,ACTIVE);gate=32.1<=t<39.9;inv+=int(num(r,p+"invalid_solve_count",0));fb+=int(num(r,p+"fallback_count",0))
  for leg in legs:
   stem=p+leg+"_hip";sel=int(num(r,stem+"_stance_selector",0));mxq=max(mxq,abs(num(r,stem+"_max_abs_delta_dq",0)));mxd=max(mxd,abs(num(r,stem+"_max_abs_delta_d_target",0)))
   for m in [x for x in mot if x.startswith(leg+"_")]:
    c=r.get(p+m+"_baseline_dq")!=r.get(p+m+"_applied_dq")
    if c:changed+=1
    if c and not gate:issues.append(f"outside gate {i} {m}")
    if c and not sel:issues.append(f"nonstance {i} {m}")
  if len(issues)>50:break
 if mxq>2.000000001:issues.append(f"dq cap {mxq}")
 if mxd>4.000000001:issues.append(f"D cap {mxd}")
 if inv!=fb:issues.append(f"invalid/fallback {inv}/{fb}")
 if not changed:issues.append("no correction")
 return not issues,issues,{"changed_joint_events":changed,"max_abs_delta_dq":mxq,"max_abs_delta_d_target":mxd,"invalid":inv,"fallback":fb}

def metric(arm,name,rows):
 rs=window(rows,*WINDOWS[name]);me=med([num(r,"velocity_command_measured_mps") for r in rs]);ap=med([num(r,"velocity_command_applied_mps") for r in rs]);ex=med([num(r,"velocity_command_measured_mps")-num(r,"velocity_command_applied_mps") for r in rs]);roll=[abs(math.degrees(num(r,"imu_roll_rad"))) for r in rs];pitch=[abs(math.degrees(num(r,"imu_pitch_rad"))) for r in rs]
 return {"arm":arm,"window":name,"rows":len(rs),"measured_mps":me,"applied_mps":ap,"velocity_excess_mps":ex,"wbc_ax_mps2":med([num(r,"wbc_full_requested_acc_x_mps2") for r in rs]),"srbd_ax_mps2":med([num(r,"wbc_full_srbd_acc_x_mps2") for r in rs]),"id_qdd_x_mps2":med([num(r,"wbc_full_id_qdd_x_mps2") for r in rs]),"roll_p95_deg":q(roll,.95),"roll_max_deg":max(roll,default=math.nan),"pitch_p95_deg":q(pitch,.95),"pitch_max_deg":max(pitch,default=math.nan),"overspeed_peak_mps":max((num(r,"velocity_command_measured_mps")-num(r,"velocity_command_applied_mps") for r in rs),default=math.nan)}

def settling(rows):
 rs=[r for r in rows if math.isfinite(num(r,ACTIVE))];seen=False;start=None
 for i,r in enumerate(rs):
  a=num(r,"velocity_command_applied_mps");seen=seen or a<=1.5
  if seen and a>=2.29:start=i;break
 if start is None:return math.nan
 t0=num(rs[start],ACTIVE)
 for i in range(start,len(rs)):
  t=num(rs[i],ACTIVE);j=i;ok=True
  while j<len(rs) and num(rs[j],ACTIVE)<t+.5:
   if abs(num(rs[j],"velocity_command_measured_mps")-num(rs[j],"velocity_command_applied_mps"))>.15:ok=False;break
   j+=1
  if ok and j<len(rs) and num(rs[j-1],ACTIVE)>=t+.498:return t-t0
 return math.nan

def sh(path):
 h=hashlib.sha256();
 with path.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--runs-root",type=Path,required=True);ap.add_argument("--output-dir",type=Path,required=True);ap.add_argument("--a-gate-only",action="store_true");x=ap.parse_args();out=x.output_dir.resolve();out.mkdir(parents=True,exist_ok=True);root=Path(__file__).resolve().parents[4];base=loadmod(Path(__file__).with_name("analyze_phase1_lockstep_baseline.py"),"d4base");rd={a:x.runs_root.resolve()/a for a in ("A","B")}
 a=read(rd["A"]/"data.csv");am=base.meta(rd["A"]/"run_metadata.txt");ag,why,pg,pi,ex=a_gate(base,rd["A"],a,am);write(out/"protocol_gates.csv",pg);write(out/"a_gate.csv",[{"pass":ag,"reasons":";".join(why),"excess":ex,**pi}])
 if x.a_gate_only:print("A_GATE_PASS" if ag else "BASELINE_GATE_FAILED");return 0 if ag else 2
 b=read(rd["B"]/"data.csv");bm=base.meta(rd["B"]/"run_metadata.txt");bg,bs=base.protocol(rd["B"],"B");bp,bpi=paired(rd["B"]);write(out/"protocol_gates.csv",pg+bg);pre,pr=pre_exact(a,b);write(out/"prewindow_exact.csv",pr);iso,iss,ist=isolation(a,b);write(out/"isolation.csv",[{"pass":iso,"issues":";".join(iss),**ist}]);mm=[metric(arm,w,a if arm=="A" else b) for arm in ("A","B") for w in WINDOWS];write(out/"ab.csv",mm);d={(r["arm"],r["window"]):r for r in mm};did=(d[("B","full")]["velocity_excess_mps"]-d[("B","pre")]["velocity_excess_mps"])-(d[("A","full")]["velocity_excess_mps"]-d[("A","pre")]["velocity_excess_mps"]);sa,sb=settling(a),settling(b);worse=math.isfinite(sa) and (not math.isfinite(sb) or sb>sa+.25);safe=all(bm.get(k,"") in ("","0") for k in STATUS) and not hard(rd["B"]);prov=[]
 for arm in ("A","B"):
  m=am if arm=="A" else bm
  for n in ("data.csv","data.csv.id_closure.csv","lockstep_trace.csv","run_metadata.txt","controller.log","simulator.log"):
   p=rd[arm]/n;prov.append({"arm":arm,"artifact":n,"bytes":p.stat().st_size if p.exists() else "","sha256":sh(p) if p.exists() else "MISSING","domain_id":m.get("domain_id",""),"git_head":m.get("git_head",""),"simulator_sha256":m.get("simulator_sha256",""),"controller_sha256":m.get("controller_sha256","")})
 write(out/"provenance.csv",prov);samehead=am.get("git_head")==bm.get("git_head") and am.get("git_head","")!="";samebin=all(am.get(k)==bm.get(k) for k in ("simulator_sha256","controller_sha256","scene_sha256"));prot=ag and bs["protocol_status"]=="PASS" and bp and samehead and samebin
 if not ag:cl="BASELINE_GATE_FAILED"
 elif not prot or not iso:cl="PROTOCOL_FAILURE"
 elif not pre:cl="INCONCLUSIVE_PREWINDOW_DIVERGENCE"
 elif not safe:cl="REJECTED_FOR_SAFETY"
 elif did<=-.02 and not worse:cl="SUPPORTED"
 else:cl="NOT_SUPPORTED"
 res={"classification":cl,"DID_excess_mps":did,"prewindow_exact":pre,"isolation_pass":iso,"A_gate_pass":ag,"B_safe":safe,"settling_A_s":sa,"settling_B_s":sb,"settling_worse":worse,"paired_A":pi,"paired_B":bpi};(out/"analysis.json").write_text(json.dumps(res,indent=2,sort_keys=True)+"\n");lines=["# Phase1 D4 deterministic live A/B","",f"Top-level classification: `{cl}`","",f"- A gate: {'PASS' if ag else 'FAIL'}",f"- deterministic pre-window equality: {'PASS' if pre else 'FAIL'}",f"- B isolation: {'PASS' if iso else 'FAIL'}",f"- B safety: {'PASS' if safe else 'FAIL'}",f"- DID excess: `{did:.9f} m/s`",f"- settling A/B: `{sa}` / `{sb}` s"];(out/"RESULTS.md").write_text("\n".join(lines)+"\n");print(f"classification={cl} DID={did:.9f}");return 0
if __name__=="__main__":raise SystemExit(main())
