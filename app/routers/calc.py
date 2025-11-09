"""Calculation endpoints for financial computations."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User, Expense, DebtAccount, Goal
from app.schemas import (
    LoanPreAssessmentRequest, LoanPreAssessmentResponse,
    LoanPayoffPlanRequest, LoanPayoffPlanResponse,
    InflationForecastRequest, InflationForecastResponse,
    InflationProjection, StressTestResult, DashboardSummary
)
from app.security import get_current_user
from app.services import calculators
from app.services.compliance import get_loan_meta, get_projection_meta, get_calc_meta
from app.settings import settings


def _simulate_payoff(
    principal: float,
    annual_rate_pct: float,
    monthly_payment: float,
    max_months: int = 1200
) -> tuple[int, float]:
    """Simulate loan payoff with optional extra payments."""
    if monthly_payment <= 0 or principal <= 0:
        return 0, 0.0

    monthly_rate = annual_rate_pct / 100 / 12
    balance = principal
    months = 0
    total_interest = 0.0

    while balance > 0 and months < max_months:
        interest = balance * monthly_rate if monthly_rate > 0 else 0.0
        principal_payment = monthly_payment - interest

        if principal_payment <= 0:
            # Payment too small to cover interest; stop simulation
            break

        balance -= principal_payment
        if balance < 1e-6:
            balance = 0.0

        total_interest += interest
        months += 1

    return months, total_interest

router = APIRouter(prefix="/calc", tags=["calculations"])


@router.post("/loan-pre-assessment", response_model=LoanPreAssessmentResponse)
def loan_pre_assessment(
    request: LoanPreAssessmentRequest,
    user: User = Depends(get_current_user)
):
    """Estimate how much additional loan a user can afford."""

    base_dti = calculators.dti(request.existing_monthly_debt, request.income)

    # Maximum total debt servicing allowed under DTI guardrail
    max_debt_capacity = request.income * settings.MAX_DTI_RATIO
    affordable_emi = max(0.0, max_debt_capacity - request.existing_monthly_debt)

    estimated_principal = calculators.principal_from_emi(
        affordable_emi,
        request.annual_rate_pct,
        request.term_months
    )

    stress_tests = []

    # Stress scenario: rate rises by 2%
    stress_rate = request.annual_rate_pct + 2
    stress_emi_rate = calculators.emi(estimated_principal, stress_rate, request.term_months)
    stress_dti_rate = calculators.dti(
        request.existing_monthly_debt + stress_emi_rate,
        request.income
    )
    stress_tests.append(StressTestResult(
        scenario="Interest rate +2%",
        new_emi=round(stress_emi_rate, 2),
        dti=round(stress_dti_rate, 4),
        is_affordable=stress_dti_rate <= settings.MAX_DTI_RATIO
    ))

    # Stress scenario: income drops by 10%
    reduced_income = request.income * 0.9
    stress_dti_income = calculators.dti(
        request.existing_monthly_debt + affordable_emi,
        reduced_income
    )
    stress_tests.append(StressTestResult(
        scenario="Income -10%",
        new_emi=round(affordable_emi, 2),
        dti=round(stress_dti_income, 4),
        is_affordable=stress_dti_income <= settings.MAX_DTI_RATIO
    ))

    return LoanPreAssessmentResponse(
        dti=round(base_dti, 4),
        affordable_emi=round(affordable_emi, 2),
        estimated_principal=round(estimated_principal, 2),
        stress_tests=stress_tests,
        meta=get_loan_meta()
    )


@router.post("/loan-payoff-plan", response_model=LoanPayoffPlanResponse)
def loan_payoff_plan(
    request: LoanPayoffPlanRequest,
    user: User = Depends(get_current_user)
):
    """Calculate EMI and payoff impact of extra payments."""

    base_emi = calculators.emi(
        request.principal,
        request.annual_rate_pct,
        request.term_months
    )
    total_paid = base_emi * request.term_months
    total_interest = total_paid - request.principal

    months_saved = 0
    interest_saved = 0.0

    if request.extra_payment > 0:
        accelerated_payment = base_emi + request.extra_payment
        accel_months, accel_interest = _simulate_payoff(
            request.principal,
            request.annual_rate_pct,
            accelerated_payment
        )

        if accel_months and accel_months < request.term_months:
            months_saved = request.term_months - accel_months
            interest_saved = max(0.0, total_interest - accel_interest)

    return LoanPayoffPlanResponse(
        monthly_emi=round(base_emi, 2),
        total_interest=round(total_interest, 2),
        total_paid=round(total_paid, 2),
        months_saved=months_saved,
        interest_saved=round(interest_saved, 2),
        meta=get_calc_meta()
    )


@router.post("/inflation-forecast", response_model=InflationForecastResponse)
def inflation_forecast(
    request: InflationForecastRequest,
    user: User = Depends(get_current_user)
):
    """Project future cost of an expense given CPI assumptions."""

    projections = []
    for year in range(1, request.years + 1):
        future_cost = calculators.inflation_projection(
            request.current_price,
            request.annual_cpi_rate,
            year
        )
        projections.append(InflationProjection(
            year=year,
            estimated_price=round(future_cost, 2)
        ))

    return InflationForecastResponse(
        projections=projections,
        meta=get_projection_meta()
    )


@router.get("/dashboard", response_model=DashboardSummary)
def get_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get dashboard summary with key financial metrics.
    """
    # Fetch user data
    expenses = db.query(Expense).filter(Expense.user_id == user.id).all()
    debts = db.query(DebtAccount).filter(DebtAccount.user_id == user.id).all()
    goals = db.query(Goal).filter(Goal.user_id == user.id).all()
    
    # Calculate totals
    total_expenses = sum(e.amount for e in expenses)
    total_debt_emi = sum(d.current_emi for d in debts)
    total_income = user.monthly_net_income
    surplus = total_income - total_expenses - total_debt_emi
    
    # DTI
    dti_ratio = calculators.dti(total_debt_emi, total_income)
    
    # Safe to spend (simplified: surplus minus 20% for goals)
    goal_allocation = surplus * 0.2 if surplus > 0 else 0
    safe_spend = max(0, surplus - goal_allocation)
    
    # Fun budget
    fun_budget_amt = calculators.fun_budget(total_income, settings.DEFAULT_FUN_RATIO)
    
    # Goal progress
    total_goal_target = sum(g.target_amount for g in goals)
    total_goal_saved = sum(g.saved_amount for g in goals)
    goal_progress = (total_goal_saved / total_goal_target * 100) if total_goal_target > 0 else 0
    
    # Debt payoff ETA (simplified: total remaining / total EMI)
    total_principal_remaining = sum(d.principal for d in debts)
    debt_eta = int(total_principal_remaining / total_debt_emi) if total_debt_emi > 0 else None
    
    return DashboardSummary(
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        surplus=round(surplus, 2),
        dti=round(dti_ratio, 4),
        safe_to_spend=round(safe_spend, 2),
        fun_budget=round(fun_budget_amt, 2),
        goal_progress_pct=round(goal_progress, 2),
        debt_payoff_eta_months=debt_eta
    )