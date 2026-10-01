// Native boundary rejection of stale upstream fallback; no optimizer tuning.
#pragma once
#include <cmath>
#include <stdexcept>
#include "mjpc/planners/ilqg/planner.h"

inline void InvalidateCurrentRollouts(mjpc::iLQGPlanner& planner) {
  for (auto& trajectory : planner.trajectory) trajectory.failure = true;
}

inline const mjpc::Trajectory* RequireFreshPlan(
    mjpc::iLQGPlanner& planner, const double* state, int dimension, double time) {
  const int current = planner.BestRollout();
  const mjpc::Trajectory* best = planner.BestTrajectory();
  if (current < 0 || !best || best->failure ||
      !std::isfinite(planner.trajectory[current].total_return) ||
      !std::isfinite(best->total_return) || best->dim_state != dimension ||
      best->horizon < 2 || best->times.empty() ||
      best->states.size() < static_cast<size_t>(dimension) ||
      !std::isfinite(best->times[0]) ||
      std::abs(best->times[0] - time) > 1e-9) {
    throw std::runtime_error("MJPC has no valid current planning candidate");
  }
  const auto& candidate = planner.trajectory[current];
  if (candidate.dim_state != dimension || candidate.times.empty() ||
      candidate.states.size() < static_cast<size_t>(dimension) ||
      !std::isfinite(candidate.times[0]) ||
      std::abs(candidate.times[0] - time) > 1e-9) {
    throw std::runtime_error("MJPC current candidate state/time is stale");
  }
  for (int i = 0; i < dimension; ++i) {
    if (!std::isfinite(candidate.states[i]) ||
        std::abs(candidate.states[i] - state[i]) > 1e-9 ||
        !std::isfinite(best->states[i]) ||
        std::abs(best->states[i] - state[i]) > 1e-9) {
      throw std::runtime_error("MJPC returned stale policy fallback");
    }
  }
  return best;
}
