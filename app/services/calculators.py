"""Pure calculator functions for financial computations."""
import math
from typing import Optional


def dti(monthly_debt: float, monthly_income: float) -> float:
    """
    Calculate debt-to-income ratio.
    
    Args:
        monthly_debt: Total monthly debt payments
        monthly_income: Total monthly income
        
    Returns:
        DTI as a decimal (e.g., 0.35 for 35%)
    """
    if monthly_income <= 0:
        return 0.0
    return monthly_debt / monthly_income


def emi(principal: float, annual_rate_pct: float, term_months: int) -> float:
    """
    Calculate equated monthly installment (EMI) for a loan.
    
    Formula: EMI = P * r * (1+r)^n / ((1+r)^n - 1)
    Where: P = principal, r = monthly rate, n = term in months
    
    Args:
        principal: Loan amount
        annual_rate_pct: Annual interest rate as percentage
        term_months: Loan term in months
        
    Returns:
        Monthly EMI amount
    """
    if principal <= 0 or term_months < 1:
        return 0.0
    
    if annual_rate_pct == 0:
        # Zero interest: simple division
        return principal / term_months
    
    monthly_rate = annual_rate_pct / 100 / 12
    numerator = principal * monthly_rate * math.pow(1 + monthly_rate, term_months)
    denominator = math.pow(1 + monthly_rate, term_months) - 1
    
    if denominator == 0:
        return 0.0
    
    return numerator / denominator


def principal_from_emi(emi_value: float, annual_rate_pct: float, term_months: int) -> float:
    """
    Calculate loan principal from desired EMI.
    
    Inverse of EMI formula: P = EMI * ((1+r)^n - 1) / (r * (1+r)^n)
    
    Args:
        emi_value: Desired monthly payment
        annual_rate_pct: Annual interest rate as percentage
        term_months: Loan term in months
        
    Returns:
        Maximum affordable principal
    """
    if emi_value <= 0 or term_months < 1:
        return 0.0
    
    if annual_rate_pct == 0:
        # Zero interest
        return emi_value * term_months
    
    monthly_rate = annual_rate_pct / 100 / 12
    numerator = emi_value * (math.pow(1 + monthly_rate, term_months) - 1)
    denominator = monthly_rate * math.pow(1 + monthly_rate, term_months)
    
    if denominator == 0:
        return 0.0
    
    return numerator / denominator


def required_emi_to_finish(
    principal: float, 
    annual_rate_pct: float, 
    months_remaining: int
) -> float:
    """
    Calculate required EMI to pay off loan in given timeframe.
    
    Args:
        principal: Remaining principal balance
        annual_rate_pct: Annual interest rate as percentage
        months_remaining: Months to complete payoff
        
    Returns:
        Required monthly payment
    """
    return emi(principal, annual_rate_pct, months_remaining)


def inflation_projection(
    current_cost: float, 
    annual_cpi_pct: float, 
    years: int
) -> float:
    """
    Project future cost given inflation rate.
    
    Formula: Future = Present * (1 + rate)^years
    
    Args:
        current_cost: Current cost/price
        annual_cpi_pct: Annual inflation rate as percentage
        years: Number of years to project
        
    Returns:
        Projected future cost
    """
    if current_cost < 0 or years < 0:
        raise ValueError("Cost and years must be non-negative")
    
    rate = annual_cpi_pct / 100
    return current_cost * math.pow(1 + rate, years)


def safe_to_spend(
    current_balance: float,
    upcoming_bills: float,
    debt_minimums: float,
    reserve: float,
    goal_allocations: float
) -> float:
    """
    Calculate safe discretionary spending amount.
    
    Args:
        current_balance: Current available balance
        upcoming_bills: Upcoming fixed expenses
        debt_minimums: Minimum debt payments due
        reserve: Emergency fund allocation
        goal_allocations: Goal savings allocation
        
    Returns:
        Safe amount to spend on discretionary items
    """
    safe = current_balance - upcoming_bills - debt_minimums - reserve - goal_allocations
    return max(0.0, safe)


def fun_budget(monthly_income: float, fun_ratio: float) -> float:
    """
    Calculate recommended fun/discretionary budget.
    
    Args:
        monthly_income: Total monthly income
        fun_ratio: Percentage allocated to fun (0.0 to 1.0)
        
    Returns:
        Fun budget amount
    """
    if monthly_income < 0:
        raise ValueError("Income cannot be negative")
    if not 0 <= fun_ratio <= 1:
        raise ValueError("Fun ratio must be between 0 and 1")
    
    return monthly_income * fun_ratio