#pragma once
#include <atomic>
#include <cstdio>
#include <cstdlib>
struct PrivateBudget {
  std::atomic<long long> rollout_steps{0}, fd_step_upper_bound{0}, fd_calls{0};
  std::atomic<long long> reserved{0};
  void Check() const {
    if (rollout_steps.load()+fd_step_upper_bound.load()>reserved.load()) {
      std::fputs("DIAGNOSTIC_PRIVATE_BUDGET_PROOF_VIOLATION\n",stderr);
      std::abort();
    }
  }
};
inline PrivateBudget* active_private_budget=nullptr;
