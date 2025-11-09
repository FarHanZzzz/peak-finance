"""Calculation endpoints for financial computations."""
from typing import List
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

router = APIRouter(prefix="/calc", tags=["calculations"])


@router.post("/loan-pre-assessment", response_model=LoanPreAssessmentResponse)
def loan_pre_assessment(
    request: LoanPreAssessmentRequest,
    user: User = Depends(get_current_user)
):
    """
    Estimate loan affordability (educational only).
    
    Returns DTI, affordable EMI cap, estimated principal, and stress test scenarios.
    """
    # Base DTI
    dti = calculators.dti(request.existing_monthly_debt, request.income)
    
    # Affordable EMI cap (40% of income - existing debt)
    max_total_debt = request.income * settings.MAX_DTI_RATIO
    affordable_new_emi = max_total_debt - request.existing_monthly_debt
    affordable_new_emi = max(0, affordable_new_emi)
    
    # Estimated principal
    principal_est = calculators.principal_from_emi(
        affordable_new_emi,
        request.annual_rate_pct,
        request.term_months
    )
    
    # Stress tests
    stress_tests = []
    
    # Scenario 1: +2% interest rate
    stress_rate = request.annual_rate_pct + 2
    stress_emi_1 = calculators.emi(principal_est, stress_rate, request.term_months)
    stress_dti_1 = calculators.dti(
        request.existing_monthly_debt + stress_emi_1,
        request.income
    )
    stress_tests.append(StressTestResult(
        scenario="Interest rate +2%",
        dti=round(stress_dti_1, 4),
        affordable_emi=round(affordable_new_emi, 2),
        principal_est=round(principal_est, 2)
    ))
    
    # Scenario 2: -10% income
    stress_income = request.income * 0.9
    stress_affordable_2 = (stress_income * settings.MAX_DTI_RATIO) - request.existing_monthly_debt
    stress_affordable_2 = max(0, stress_affordable_2)
    stress_principal_2 = calculators.principal_from_emi(
        stress_affordable_2,
        request.annual_rate_pct,