import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
import torch
import mujoco
import yaml

ROOT=Path('/home/che/dev/go2-workspace/moe-cts-native-20261005')
REPO=ROOT/'repo'
COMMIT='28b4516d22617b11aeaf8ead63cc00b0c0bcd1bd'
POLICY=REPO/'deploy/pre_train/go2/go2_moe_cts_176k_0.6984.pt'
CFG=REPO/'deploy/deploy_mujoco/configs/go2.yaml'

def sha256(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def grav(q):
    qw,qx,qy,qz=q
    return np.array([2*(-qz*qx+qw*qy),-2*(qz*qy+qw*qx),1-2*(qw*qw+qz*qz)],dtype=np.float32)

def roll_pitch(q):
    w,x,y,z=[float(v) for v in q]
    sinr=2*(w*x+y*z); cosr=1-2*(x*x+y*y)
    roll=math.atan2(sinr,cosr)
    sinp=2*(w*y-z*x); pitch=math.asin(max(-1.0,min(1.0,sinp)))
    return roll,pitch

def body_vx(data):
    nq=np.zeros(4); mujoco.mju_negQuat(nq,data.qpos[3:7])
    bv=np.zeros(3); mujoco.mju_rotVecQuat(bv,data.qvel[:3],nq)
    return float(bv[0])

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--scene',choices=['flat','stairs','stairs_and_slope'],default='flat'); ap.add_argument('--seconds',type=float,default=3.0); ap.add_argument('--out',required=True); args=ap.parse_args()
    raw=yaml.safe_load(CFG.read_text())
    dt=float(raw['simulation_dt']); dec=int(raw['control_decimation'])
    steps=round(args.seconds/dt); assert abs(steps*dt-args.seconds)<1e-12
    default=np.asarray(raw['default_angles'],dtype=np.float32); kp=np.asarray(raw['kps'],dtype=np.float32); kd=np.asarray(raw['kds'],dtype=np.float32)
    cmd=np.asarray(raw['cmd_init'],dtype=np.float32); cmd_scale=np.asarray(raw['cmd_scale'],dtype=np.float32)
    maxcmd=np.asarray(raw['max_cmd'],dtype=np.float32); assert np.all(np.abs(cmd)<=maxcmd+1e-12)
    scene={'flat':'flat.xml','stairs':'stairs.xml','stairs_and_slope':'stairs_and_slope.xml'}[args.scene]
    xml=REPO/'resources/go2'/scene
    model=mujoco.MjModel.from_xml_path(str(xml)); data=mujoco.MjData(model); model.opt.timestep=dt
    data.qpos[:]=0; data.qvel[:]=0; data.qpos[:3]=np.asarray(raw['base_init_pos']); data.qpos[3:7]=np.asarray(raw['base_init_quat']); data.qpos[7:]=default; mujoco.mj_forward(model,data)
    policy=torch.jit.load(str(POLICY),map_location='cpu'); policy.eval()
    action=np.zeros(int(raw['num_actions']),dtype=np.float32); target=default.copy(); target_vel=np.zeros_like(default)
    vx=[]; heights=[]; rolls=[]; pitches=[]; ctrl_peaks=[]; action_peaks=[]; terminal='horizon'; error=None
    x0=float(data.qpos[0])
    try:
        for counter in range(1,steps+1):
            ctrl=(target-data.qpos[7:])*kp+(target_vel-data.qvel[6:])*kd
            if not np.all(np.isfinite(ctrl)): raise RuntimeError('nonfinite_ctrl')
            data.ctrl[:]=ctrl; mujoco.mj_step(model,data)
            if not (np.all(np.isfinite(data.qpos)) and np.all(np.isfinite(data.qvel))): raise RuntimeError('nonfinite_state')
            v=body_vx(data); r,p=roll_pitch(data.qpos[3:7]); vx.append(v); heights.append(float(data.qpos[2])); rolls.append(abs(r)); pitches.append(abs(p)); ctrl_peaks.append(float(np.max(np.abs(ctrl))))
            if counter%dec==0:
                jp=(data.qpos[7:]-default)*float(raw['dof_pos_scale']); jv=data.qvel[6:]*float(raw['dof_vel_scale'])
                single=np.concatenate([data.qvel[3:6]*float(raw['ang_vel_scale']),grav(data.qpos[3:7]),cmd*cmd_scale,jp,jv,action]).astype(np.float32,copy=False)
                if single.shape!=(int(raw['num_obs']),): raise RuntimeError(f'obs_shape_{single.shape}')
                with torch.no_grad(): out=policy(torch.from_numpy(single).unsqueeze(0))
                action=out.detach().cpu().numpy().squeeze().astype(np.float32,copy=False)
                if action.shape!=(int(raw['num_actions']),) or not np.all(np.isfinite(action)): raise RuntimeError('bad_action')
                action_peaks.append(float(np.max(np.abs(action))))
                target=default+action*float(raw['action_pos_scale'])
    except Exception as e:
        terminal='error'; error=f'{type(e).__name__}: {e}'
    arr=np.asarray(vx,dtype=float); tail=arr[-min(len(arr),round(1.0/dt)):] if len(arr) else arr
    result={'kind':'engineering_native_headless_smoke','repo_commit':COMMIT,'policy_sha256':sha256(POLICY),'policy':str(POLICY.relative_to(REPO)),'scene':scene,'command':cmd.tolist(),'dt_s':dt,'control_decimation':dec,'control_hz':1/(dt*dec),'requested_seconds':args.seconds,'executed_steps':len(vx),'terminal':terminal,'error':error,'progress_x_m':float(data.qpos[0]-x0),'final_xyz_m':[float(x) for x in data.qpos[:3]],'body_vx_mean_all_mps':float(arr.mean()) if len(arr) else None,'body_vx_mean_last1s_mps':float(tail.mean()) if len(tail) else None,'body_vx_min_mps':float(arr.min()) if len(arr) else None,'body_vx_max_mps':float(arr.max()) if len(arr) else None,'height_min_m':min(heights) if heights else None,'height_max_m':max(heights) if heights else None,'max_abs_roll_rad':max(rolls) if rolls else None,'max_abs_pitch_rad':max(pitches) if pitches else None,'max_abs_pd_ctrl':max(ctrl_peaks) if ctrl_peaks else None,'max_abs_policy_action':max(action_peaks) if action_peaks else None,'policy_updates':len(action_peaks)}
    Path(args.out).write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2)); raise SystemExit(0 if terminal=='horizon' else 2)
if __name__=='__main__': main()
