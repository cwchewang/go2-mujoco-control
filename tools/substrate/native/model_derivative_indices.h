#pragma once

#include <stdexcept>
#include <vector>

namespace go2_substrate {

// Reproduces MJPC's derivative sampling order while avoiding appending T-2
// twice when the regular stride already selected it.
inline std::vector<int> ModelDerivativeEvaluateIndices(int horizon, int skip) {
  if (horizon < 2) {
    throw std::invalid_argument("model derivative horizon must be at least 2");
  }
  if (skip < 0) {
    throw std::invalid_argument("model derivative skip must be nonnegative");
  }

  const int stride = skip + 1;
  std::vector<int> evaluate{0};
  for (int t = stride; t < horizon - stride; t += stride) {
    evaluate.push_back(t);
  }
  if (evaluate.back() != horizon - 2) {
    evaluate.push_back(horizon - 2);
  }
  evaluate.push_back(horizon - 1);
  return evaluate;
}

}  // namespace go2_substrate
