#include <cmath>
#include <iostream>

#include <Eigen/Dense>

#include "dense_qp.h"

namespace
{

bool Near(double actual, double expected, double tolerance = 1e-6)
{
    return std::abs(actual - expected) <= tolerance;
}

bool CheckUnconstrained()
{
    Eigen::MatrixXd H(1, 1);
    H(0, 0) = 1.0;
    Eigen::VectorXd g(1);
    g[0] = -2.0;
    Eigen::MatrixXd A(0, 1);
    Eigen::VectorXd b(0);
    Eigen::VectorXd x;
    int iterations = 0;
    return go2_control::SolveDenseQp(H, g, A, b, x, iterations) &&
           x.size() == 1 && Near(x[0], 2.0);
}

bool CheckBound()
{
    Eigen::MatrixXd H(1, 1);
    H(0, 0) = 1.0;
    Eigen::VectorXd g(1);
    g[0] = -2.0;
    Eigen::MatrixXd A(1, 1);
    A(0, 0) = 1.0;
    Eigen::VectorXd b(1);
    b[0] = 0.5;
    Eigen::VectorXd x;
    int iterations = 0;
    return go2_control::SolveDenseQp(H, g, A, b, x, iterations) &&
           x.size() == 1 && Near(x[0], 0.5, 1e-5);
}

bool CheckTwoSided()
{
    Eigen::MatrixXd H = Eigen::MatrixXd::Identity(2, 2);
    Eigen::VectorXd g = Eigen::VectorXd::Zero(2);
    Eigen::MatrixXd A(1, 2);
    A << -1.0, 0.0;
    Eigen::VectorXd b(1);
    b[0] = -1.0;
    Eigen::VectorXd x;
    int iterations = 0;
    return go2_control::SolveDenseQp(H, g, A, b, x, iterations) &&
           Near(x[0], 1.0, 1e-5) && Near(x[1], 0.0, 1e-5);
}

bool CheckEqualityKkt()
{
    Eigen::MatrixXd H = Eigen::MatrixXd::Identity(2, 2);
    Eigen::VectorXd g = Eigen::VectorXd::Zero(2);
    Eigen::MatrixXd Aineq(0, 2);
    Eigen::VectorXd bineq(0);
    Eigen::MatrixXd Aeq(1, 2);
    Aeq << 1.0, 1.0;
    Eigen::VectorXd beq(1);
    beq[0] = 1.0;
    Eigen::VectorXd x;
    int iterations = 0;
    return go2_control::SolveDenseQpEq(
               H, g, Aineq, bineq, Aeq, beq, x, iterations) &&
           Near(x[0], 0.5, 1e-6) && Near(x[1], 0.5, 1e-6);
}

bool CheckEqualityWithBound()
{
    Eigen::MatrixXd H = Eigen::MatrixXd::Identity(2, 2);
    Eigen::VectorXd g = Eigen::VectorXd::Zero(2);
    Eigen::MatrixXd Aineq(1, 2);
    Aineq << 1.0, 0.0;
    Eigen::VectorXd bineq(1);
    bineq[0] = 0.2;
    Eigen::MatrixXd Aeq(1, 2);
    Aeq << 1.0, 1.0;
    Eigen::VectorXd beq(1);
    beq[0] = 1.0;
    Eigen::VectorXd x;
    int iterations = 0;
    return go2_control::SolveDenseQpEq(
               H, g, Aineq, bineq, Aeq, beq, x, iterations) &&
           Near(x[0], 0.2, 1e-4) && Near(x[1], 0.8, 1e-4);
}

bool CheckStrictConstrainedAcceptance()
{
    // x == 0 has zero equality residual, while x <= -1 is infeasible.  A
    // short deterministic run must not be promoted by the equality residual.
    Eigen::MatrixXd H = Eigen::MatrixXd::Identity(1, 1);
    Eigen::VectorXd g = Eigen::VectorXd::Zero(1);
    Eigen::MatrixXd Aineq(1, 1);
    Aineq(0, 0) = 1.0;
    Eigen::VectorXd bineq(1);
    bineq[0] = -1.0;
    Eigen::MatrixXd Aeq(1, 1);
    Aeq(0, 0) = 1.0;
    Eigen::VectorXd beq(1);
    beq[0] = 0.0;
    Eigen::VectorXd x;
    int iterations = 0;
    go2_control::DenseQpSettings settings;
    settings.max_iterations = 1;
    settings.feasibility_tol = 1.0e-6;
    const bool solver_accepted = go2_control::SolveDenseQpEq(
        H, g, Aineq, bineq, Aeq, beq, x, iterations, settings);
    const double equality_residual =
        x.size() == 1 ? std::abs((Aeq * x - beq)[0]) : 1.0;
    const bool clean_accepts = solver_accepted &&
        equality_residual <= settings.feasibility_tol;
    return !solver_accepted && equality_residual <= settings.feasibility_tol &&
           !clean_accepts;
}

}  // namespace

int main()
{
    if (!CheckUnconstrained() || !CheckBound() || !CheckTwoSided() ||
        !CheckEqualityKkt() || !CheckEqualityWithBound() ||
        !CheckStrictConstrainedAcceptance())
    {
        std::cerr << "dense QP checks failed\n";
        return 1;
    }
    std::cout << "dense QP checks passed.\n";
    return 0;
}
