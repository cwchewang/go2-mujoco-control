"""Fixed-only 3 s MJPC baseline. Prepare/preflight never launch MJPC or integrate."""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys
from dataclasses import replace
from pathlib import Path
from . import fd_duplicate_diagnostic as build
from .aligned_anchor import load_anchor
from .aligned_episode import run_aligned_episode
from .contracts import PositionTargetControllerAdapter
from .episode import MujocoPlant
from .guards import zero_step_guard, wall_deadline
from .integrity import EvidenceRun, digest, experiment_lock, strict_json, verify_manifest, write_new
from .native_mjpc import NativeMJPCController

ROOT=Path(__file__).resolve().parents[2]
RUNS=ROOT/"_runs"
FIXED=ROOT/"_runs/mjpc_short_sequence_evidence_launcherfix_20261003/go2_mjpc_controller_fd_fixed"
BINARY_SHA="3644c6160dae354319c94840bdd07ca12166500a2b133f97b78421f8db587b08"
PROTOCOL=ROOT/"tools/substrate/protocols/mjpc_fixed_baseline_3s_v1.json"
RUNTIME=("tools/substrate/mjpc_fixed_baseline.py","tools/substrate/aligned_episode.py","tools/substrate/aligned_anchor.py","tools/substrate/native_mjpc.py","tools/substrate/native_transport.py","tools/substrate/contracts.py","tools/substrate/episode.py","tools/substrate/evaluator.py","tools/substrate/clock.py","tools/substrate/guards.py","tools/substrate/integrity.py","tools/substrate/build_identity.py","tools/substrate/protocols/aligned_flat_anchor_v1.json","tools/substrate/protocols/mjpc_fixed_baseline_3s_v1.json")

def git(*a): return subprocess.check_output(["git",*a],cwd=ROOT,text=True).strip()
def identity():
    branch=git("branch","--show-current")
    if branch!="research/mjpc-fd-duplicate-fix-20261003" or git("status","--porcelain"): raise ValueError("requires clean named research branch")
    return {"branch":branch,"head":git("rev-parse","HEAD")}
def design():
    return {"repeats":2,"workers":4,"horizon_s":3.0,"canonical_steps":1500,"replans":150,
      "private_reservation_per_replan":4096,"private_upper_bound_per_repeat":614400,
      "private_upper_bound_total":1228800,"binary_sha256":BINARY_SHA,
      "anchor":"aligned-flat-forward-integration-v1","zero_command_ticks":50,"ramp_ticks":100,
      "failure_policy":"stop pair on first safety/execution/evidence/budget failure; no retry",
      "pass":"both fresh-process episodes reach 1500 ticks with canonical classification HORIZON_REACHED",
      "capability_claim":"none"}
def runtime_identity(): return {p:digest(ROOT/p) for p in RUNTIME}
def fresh(path):
    p=Path(path).expanduser().resolve()
    if p.parent!=RUNS.resolve(strict=True) or p.exists(): raise ValueError("output must be a fresh direct child of _runs")
    return p
def prepare(output,binary=FIXED):
    with experiment_lock(),zero_step_guard():
        ident=identity()
        if strict_json(PROTOCOL.read_text())!=design(): raise ValueError("protocol drift")
        bi=build.build_identity(binary,"fixed")
        if bi["binary_sha256"]!=BINARY_SHA or bi["workers"]!=4: raise ValueError("fixed binary identity/workers mismatch")
        out=fresh(output)
        packet={"schema":1,"kind":"mjpc-fixed-baseline-3s-v1",**ident,"design":design(),
          "runtime":runtime_identity(),"protocol_sha256":digest(PROTOCOL),
          "anchor_sha256":digest(ROOT/"tools/substrate/protocols/aligned_flat_anchor_v1.json"),"build":bi,
          "binary":{"name":"go2_mjpc_controller_fd_fixed","sha256":BINARY_SHA}}
        with EvidenceRun(out,{"operation":"mjpc_fixed_baseline_prepare",**ident}) as run:
            target=out/packet["binary"]["name"]; shutil.copy2(binary,target)
            if digest(target)!=BINARY_SHA: raise ValueError("copied binary digest mismatch")
            write_new(out/"packet.json",packet)
            run.result.update(status="PREPARED_NOT_RUN",scope="fixed_baseline_prepare",
              canonical_physics_steps=0,native_processes_started=0,scientific_attempts=0)
        verify_manifest(out)
        return {"status":"PREPARED_NOT_RUN","packet":str(out/"packet.json"),"packet_sha256":digest(out/"packet.json"),**ident}
def validate(packet_path,output):
    out=fresh(output); pp=Path(packet_path).resolve(strict=True)
    if pp.name!="packet.json" or pp.parent.parent!=RUNS.resolve(strict=True): raise ValueError("packet must be in direct-child _runs bundle")
    manifest=verify_manifest(pp.parent); packet=strict_json(pp.read_text()); ident=identity()
    if manifest.get("status")!="PREPARED_NOT_RUN" or any(packet.get(k)!=ident[k] for k in ("branch","head")): raise ValueError("stale preparation")
    if packet.get("kind")!="mjpc-fixed-baseline-3s-v1" or packet.get("design")!=design(): raise ValueError("design mismatch")
    if packet.get("runtime")!=runtime_identity() or packet.get("protocol_sha256")!=digest(PROTOCOL) or packet.get("anchor_sha256")!=digest(ROOT/"tools/substrate/protocols/aligned_flat_anchor_v1.json"): raise ValueError("runtime/protocol/anchor drift")
    binary=pp.parent/packet["binary"]["name"]; bi=build.build_identity(binary,"fixed")
    if {k:v for k,v in bi.items() if k!="path"}!={k:v for k,v in packet.get("build",{}).items() if k!="path"} or digest(binary)!=BINARY_SHA or bi["workers"]!=4: raise ValueError("binary/workers mismatch")
    anchor=load_anchor(); task=replace(anchor["task"],task_id="mjpc-fixed-baseline-3s-v1",horizon_ticks=1500,measurement_start_tick=150)
    timing=anchor["controllers"]["mjpc"]["timing"]; plant=MujocoPlant(ROOT/anchor["scenario"].scene)
    if plant.steps!=0 or float(plant.data.time)!=0.0 or plant.model.opt.timestep!=timing.physics_period_s: raise ValueError("zero-step plant/timing check")
    if task.command_at(0).tolist()!=[0.,0.,0.] or task.command_at(150).tolist()!=[1.,0.,0.]: raise ValueError("task command mismatch")
    return packet,binary,{"status":"PRECHECK_PASS","branch":ident["branch"],"head":ident["head"],
      "packet_sha256":digest(pp),"prepared_manifest_sha256":digest(pp.parent/"manifest.json"),
      "output":str(out),"fixed_binary_sha256":digest(binary),"workers":4,
      "canonical_physics_steps":0,"native_processes_started":0,"optimizer_calls":0,"experiment_lock":"held"}
def no_launch(packet_path,output):
    with experiment_lock(),zero_step_guard():
        packet,binary,report=validate(packet_path,output); out=Path(report["output"])
        with EvidenceRun(out,{"operation":"mjpc_fixed_baseline_preflight","head":report["head"]}) as run:
            write_new(out/"preflight.json",report)
            run.result.update(status="PRECHECK_PASS_NO_LAUNCH",canonical_physics_steps=0,native_processes_started=0,scientific_attempts=0)
        verify_manifest(out)
        return {**report,"status":"PRECHECK_PASS_NO_LAUNCH","manifest_sha256":digest(out/"manifest.json")}
def run_one(packet_path,output):
    """Capture primitive used only after a separate reviewed START gate."""
    packet,binary,_=validate(packet_path,Path(output).parent/(Path(output).name+"_preflight"))
    anchor=load_anchor(); task=replace(anchor["task"],task_id="mjpc-fixed-baseline-3s-v1",horizon_ticks=1500,measurement_start_tick=150)
    timing=anchor["controllers"]["mjpc"]["timing"]; info=anchor["controllers"]["mjpc"]["information"]; plant=MujocoPlant(ROOT/anchor["scenario"].scene)
    native=NativeMJPCController(binary,timing,stderr_log_path=Path(output)/"native.stderr.log")
    controller=PositionTargetControllerAdapter(native,native.actuator_spec,native.joint_names); consumed=False
    def consume():
        nonlocal consumed
        if consumed: raise ValueError("attempt already consumed")
        consumed=True
    try:
        with (Path(output)/"raw.jsonl").open("x") as stream:
            def emit(row): stream.write(json.dumps(row,allow_nan=False,sort_keys=True)+"\\n"); stream.flush()
            with wall_deadline(300): outcome=run_aligned_episode(plant,controller,task,info,timing,emit,consume)
        (Path(output)/"native-diagnostics.json").write_text(json.dumps(native.diagnostics(),sort_keys=True)+"\\n")
    finally: native.close()
    return {"outcome":outcome,"canonical_physics_steps":plant.steps,"attempt_consumed":consumed,
      "classification":"HORIZON_REACHED" if outcome["terminal_reason"]=="horizon" else "SAFETY_STOP"}
def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__); g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--prepare",action="store_true"); g.add_argument("--preflight",action="store_true")
    p.add_argument("--packet",type=Path); p.add_argument("--binary",type=Path,default=FIXED); p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(argv); os.chdir(ROOT)
    if a.prepare:
        if a.packet: p.error("--prepare does not accept --packet")
        result=prepare(a.output,a.binary)
    else:
        if not a.packet: p.error("--preflight requires --packet")
        result=no_launch(a.packet,a.output)
    print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__": main()

