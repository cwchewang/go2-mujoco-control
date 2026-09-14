# Phase1 lockstep baseline determinism

Hypothesis: removing wall-clock scheduling from the simulator/controller exchange preserves the existing varying-command baseline and makes the state/command pairing auditable.

Scope: three sequential L1/L2/L3 launches of the existing varying profile; period=0.14 s, duty=0.44, D4=OFF. No D4 or gain/threshold/analyzer change was introduced.

Authority source HEAD at launch: 5a1559d6456975bd340a426edc71b85fde16ceaa.
Scene SHA256: 12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8.
Profile SHA256: 9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74.

Checkpoint gate: FAIL. The strict one-command-update gate is the limiting result; see protocol_gates.csv.

Protocol status is reported separately from the legacy physical/safety status. protocol_gates.csv is the checkpoint gate; run_summary.csv records observed run and legacy statuses; pairwise.csv compares common controller timestamps only.

The three runs used run_phase1_lockstep_baseline.sh L1, then L2, then L3, with DDS domains 201, 202, and 203. Each run used the frozen Phase1 varying command and lockstep simulator flag.

## Per-run result

|run|protocol|trace rows|intervals|dt ms|violations|legacy controller|safety|quality|
|---|---|---:|---:|---:|---|---:|---:|---:|
|L1|FAIL|42476|42475|2|0|0|0|0|
|L2|FAIL|42687|42686|2|0|0|0|0|
|L3|FAIL|42476|42475|2|0|0|0|0|

## Provenance hashes

|run|simulator SHA256|controller SHA256|data.csv SHA256|trace SHA256|
|---|---|---|---|---|
|L1|b23def48a329e02b1c9b9afc3e4056c2e78d0ecc59de366d3573cdccc68c1319|7d3ba23cb7217e4b67c467510aea047d06da9104a5ab423cbf943b4e41713119|295c5b0b3286ed59f6c982b23f5f818376cc37f7cc1d47cb5a296b811b8d973d|96fa7c2dd1b08aa17e240ca4ff6203d4fcad1142d0d8023c04a47bb19847a00f|
|L2|b23def48a329e02b1c9b9afc3e4056c2e78d0ecc59de366d3573cdccc68c1319|7d3ba23cb7217e4b67c467510aea047d06da9104a5ab423cbf943b4e41713119|f9d7293220461869b071d7f3289004ad36a1465e10e1fc3453d08e2e782da241|726c9f993b3ee6ba6247422446c204519be3a1b24f143299bc456f1cbade52bd|
|L3|b23def48a329e02b1c9b9afc3e4056c2e78d0ecc59de366d3573cdccc68c1319|7d3ba23cb7217e4b67c467510aea047d06da9104a5ab423cbf943b4e41713119|c23639c47b5fe0c1b74f5155b3818fe896a24235649d8f27add95dc16a2e7f92|c731ac832610bcde91486ed64d81551e5c4841b2e52e67de58b235dc9b62e442|

Scoped source SHA256:
- simulate/src/lockstep.h: 5d29ba586502dae03aa62bf435f6e21f72e77aea565ddf9358ffe557f39a0c09
- simulate/src/main.cc: 9b9c6efa310802ba3a2db0fc796f141056dceec70f7b91a9e654cabbbaf4ecaf
- simulate/src/unitree_sdk2_bridge.h: 5bbf284c926c87c63588057dc90af308ef3e7d360830463af8e82cc1edd0d9e9
- example/cpp/trot/lockstep_writer_gate.h: 74607d9e48f0dd3092320d31743d50494068c395cd7c00bad52f22ccfaa2e0c7
- example/cpp/trot/lockstep_motion_clock.h: 704a352e39164d22fe74457f4cb9a6fb57f94e7222dfca6dd707ac135603add8
- example/cpp/trot/trot_experiment_lifecycle.cpp: e51a871bd9ea513d7dfa04abf11f306630e2568a01fcc33acb13b664006ad914
- example/cpp/trot/trot_experiment_control.cpp: 9e63cbfbcff1dd7c984e374370612ff9c44c785c6b123356cbd9dd9dbbe42a0a
- example/cpp/scripts/run_trot.sh: 98c93ed801b04dd6032a0eee21d66a696d94d3dd3df47b40cde049be64c0bee1
- example/cpp/scripts/run_phase1_lockstep_baseline.sh: 42aca2fbf01221c0700a65478d8c98c2aaa46c4215b10467ae1633a8f4348c45

## Classification

The lockstep protocol is PASS only when every protocol gate is PASS. Physical/safety failures, if present, are reported as observed baseline outcomes and are not converted into protocol failures. Pairwise values are descriptive determinism evidence; no wall-clock comparison or new acceptance threshold is introduced.

## Reproduction

Build the simulator and controller targets from the task, then invoke the three runner commands sequentially. Raw run directories remain under _runs/phase1_lockstep_baseline_determinism_20260914/.

## Checkpoint boundary

This is one lockstep baseline determinism checkpoint. No D4, counterfactual, lag, gain, threshold, or additional experiment was run after L1/L2/L3.
