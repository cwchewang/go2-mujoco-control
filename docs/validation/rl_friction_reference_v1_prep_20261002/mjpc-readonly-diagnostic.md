# Sealed MJPC baseline1 read-only diagnosis

Scope: source-locked raw/source inspection only; no controller, optimizer,
integration or new MJPC physics. Parent closeout remains unchanged.
Capture head `b1ac4f700cc0f8ed3bd431e28a230bc1ae71058d`;
capture manifest SHA256
`66630a6c749c10891e59cfd454c7cf3174d7c310ac65ddd73076308a49a9bf8f`;
MJPC raw SHA256
`e5f760c54a57d12e8da6150972cb084414c3f9d84f1827ac9582b292532a3841`.
The independent worker checked these hashes and matching model/source.

## Actual contact constraints and drop

Raw has1288 frames0..1287 and1287 action frames. Its `supports` are active
foot-floor contact constraints (`efc_address>=0`), as emitted in
[episode.py](../../../tools/substrate/episode.py). Raw has no contact forces,
so these sets do not measure load fractions or internal planner gait phase.
There are72 contact-set continuous segments. Across action frames, FL+RR397,
FR+RL340, all-four105 and empty130; other frames have other contact sets.
Complete no-foot-contact segments are132–175,404–419,822–829 and1225–1287.

RR foot last contact is tick1167/2.334s. Final contact sets:

| ticks | time/s | contact set |
|---|---:|---|
|1065–1167|2.130–2.334|FL+RR|
|1168–1172|2.336–2.344|FL|
|1173|2.346|FL+RL|
|1174–1186|2.348–2.372|FL+FR+RL|
|1187–1190|2.374–2.380|FL+FR|
|1191–1192|2.382–2.384|FL+FR+RL|
|1193–1221|2.386–2.442|FR+RL|
|1222–1224|2.444–2.448|FR|
|1225–1287|2.450–2.574|empty|

Final height peak is tick1240/2.480s at0.345262356m. It then drops40.039527mm
over94ms to0.305222830m, with terminal vertical velocity−0.912632m/s and
tilt0.329593rad. Those posture values stay within frozen limits; actual STOP is
`nonfoot_contact`, forbidden pair[0,53] (floor/RR_calf), at2.574s.
Earlier zero-integration reconstruction in the closeout confirmed that pair
with positive contact distance0.000804116m; no penetration/impact claim follows.

The existing v2 first501-frame prefix first differs in actual contact set at
tick113 (this capture FL+RR, v2 RR), with142 differing sets overall. This
observed difference does not identify a mechanism or deployment bug.

## Joint targets and tracking

Canonical qpos leg order is FL,FR,RL,RR; raw target/action motor order is
FR,FL,RR,RL. RR calf actual state is qpos[18]/qvel[17], target/control index8
(zero-based). Rebuilding all raw `60*(target−q)−5*qvel` with the correct mapping
matches logged pd exactly (maximum error0).

| calf | full action-frame MAE/rad | max absolute target error/rad |
|---|---:|---:|
|FR|0.281181|1.486131|
|FL|0.275816|0.965246|
|RR|0.266329|0.994568 at tick161|
|RL|0.226660|1.074771|

RR calf target range is[−2.476205,−0.837760]rad; actual range is
[−1.939140,−1.222927]rad. At the last action tick1286, target−2.069156300,
actual−1.885797277, error−0.183359023rad and ctrl+1.623727030Nm, without clip.
Terminal1287 actual is−1.890298180rad with null target/action. The last global
motor clip is1075/2.150s; RR calf last clip675/1.350s; outer position clips0.
These observations alone do not show that tracking error caused the contact.

## Private prediction evidence boundary

[controller.cc](../../../tools/substrate/native/controller.cc)289–302 and
[native_mjpc.py](../../../tools/substrate/native_mjpc.py)126–167 emit/receive
cost, replanned, current_rollout_valid, timing and q_des only. The sealed
members have no predicted states/contacts, internal phase, candidate IDs,
stepwise predicted costs or model prediction errors. The valid scalar for all
1287 feedback/129 planning calls does not verify predicted landing/contact
agreement with actual physics.

The first two divergence lines are first observed by raw at tick110/0.220s
and140/0.280s. Four more divergences plus private QACC Time2.7900 first appear
together at canonical tick1230/2.460s. Cumulative/asynchronous stderr lacks
candidate IDs and exact canonical event timestamps; private future time is
not canonical warning time. Canonical warning_count stays0.

Observed order is: all-foot contact constraints disappear2.450s; new stderr is
first observed2.460s; final height peak2.480s; RR calf-floor STOP2.574s.
No causal chain connecting prediction error, candidate divergence, joint
tracking and terminal contact is established. Missing prediction evidence
remains a stated limitation; no rerun is performed.
