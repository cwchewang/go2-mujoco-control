// Synthetic upstream public trajectory fixtures: no physics integration.
#include <iostream>
#include <stdexcept>
#include "fresh_plan.h"

void RequireReject(mjpc::iLQGPlanner& p, const double* state) {
  try { RequireFreshPlan(p, state, 2, 1.0); }
  catch (const std::runtime_error&) { return; }
  throw std::runtime_error("stale/all-failed plan was accepted");
}

int main() {
  try {
    mjpc::iLQGPlanner p;
    auto& old = p.policy.trajectory;
    old.Initialize(2, 1, 1, 0, 2);
    old.Allocate(2);
    old.Reset(2);
    old.failure = false;
    old.total_return = 1;
    old.times[0] = 0;
    old.states[0] = 1;
    old.states[1] = 2;
    const double state[2] = {1, 2};
    // Finite old policy cannot rescue an all-failed current batch.
    InvalidateCurrentRollouts(p);
    RequireReject(p, state);
    p.trajectory[0] = old;
    p.trajectory[0].failure = false;
    // A current candidate does not make stale policy time/state acceptable.
    RequireReject(p, state);
    old.times[0] = 1;
    old.states[0] = 99;
    RequireReject(p, state);
    old.states[0] = 1;
    p.trajectory[0] = old;
    RequireFreshPlan(p, state, 2, 1.0);
    InvalidateCurrentRollouts(p);
    RequireReject(p, state);
    std::cout << "{\"all_failed_rejected\":true,\"stale_fallback_rejected\":true,"
                 "\"fresh_candidate_accepted\":true,\"physics_integrations\":0}\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
