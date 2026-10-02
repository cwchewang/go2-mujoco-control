#include "model_derivative_indices.h"

#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <utility>
#include <vector>

namespace {

void Require(bool condition, const char* message) {
  if (!condition) {
    std::cerr << message << "\n";
    std::exit(1);
  }
}

std::vector<int> LegacyIndices(int horizon, int skip) {
  const int stride = skip + 1;
  std::vector<int> indices{0};
  for (int t = stride; t < horizon - stride; t += stride) {
    indices.push_back(t);
  }
  indices.push_back(horizon - 2);
  indices.push_back(horizon - 1);
  return indices;
}

void TestLegacyRegression() {
  const auto old_indices = LegacyIndices(36, 0);
  Require(old_indices.size() == 37, "legacy T=36, skip=0 length changed");
  Require(std::count(old_indices.begin(), old_indices.end(), 34) == 2,
          "legacy T=36, skip=0 no longer exposes duplicate t=34");
}

void TestPreservesOrderAndRequiredIndices() {
  for (int horizon = 2; horizon <= 40; ++horizon) {
    for (int skip = 0; skip <= 16; ++skip) {
      auto expected = LegacyIndices(horizon, skip);
      expected.erase(std::unique(expected.begin(), expected.end()),
                     expected.end());
      const auto actual =
          go2_substrate::ModelDerivativeEvaluateIndices(horizon, skip);
      Require(actual == expected,
              "patched order differs from deduplicated legacy order");
      Require(std::adjacent_find(actual.begin(), actual.end()) == actual.end(),
              "patched derivative indices contain a duplicate");
      Require(actual.front() == 0, "first derivative index must be 0");
      Require(actual.back() == horizon - 1, "last derivative index missing");
      Require(std::find(actual.begin(), actual.end(), horizon - 2) != actual.end(),
              "penultimate derivative index missing");
    }
  }
}

void TestBoundaries() {
  Require((go2_substrate::ModelDerivativeEvaluateIndices(2, 0) ==
           std::vector<int>{0, 1}), "minimum horizon/zero skip failed");
  Require((go2_substrate::ModelDerivativeEvaluateIndices(2, 16) ==
           std::vector<int>{0, 1}), "minimum horizon/maximum GUI skip failed");
  for (const auto& args : {std::pair{1, 0}, std::pair{2, -1}}) {
    bool rejected = false;
    try {
      (void)go2_substrate::ModelDerivativeEvaluateIndices(args.first, args.second);
    } catch (const std::invalid_argument&) {
      rejected = true;
    }
    Require(rejected, "invalid horizon or skip was accepted");
  }
}

}  // namespace

int main() {
  TestLegacyRegression();
  TestPreservesOrderAndRequiredIndices();
  TestBoundaries();
}
