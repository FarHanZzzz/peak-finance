"""CRUD routes for expenses, debts, goals."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User, Expense, DebtAccount, Goal
from app.schemas import (
    ExpenseCreate, ExpenseResponse,
    DebtCreate, DebtResponse,
    GoalCreate, GoalResponse
)
from app.security import get_current_user

router = APIRouter(prefix="/data", tags=["data"])


# ============ EXPENSES ============
@router.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    expense_data: ExpenseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Create a new expense."""
    expense = Expense(**expense_data.dict(), user_id=user.id)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.get("/expenses", response_model=List[ExpenseResponse])
def list_expenses(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """List user's expenses."""
    expenses = db.query(Expense).filter(Expense.user_id == user.id).all()
    return expenses


# ============ DEBTS ============
@router.post("/debts", response_model=DebtResponse, status_code=status.HTTP_201_CREATED)
def create_debt(
    debt_data: DebtCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Create a new debt account."""
    debt = DebtAccount(**debt_data.dict(), user_id=user.id)
    db.add(debt)
    db.commit()
    db.refresh(debt)
    return debt


@router.get("/debts", response_model=List[DebtResponse])
def list_debts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """List user's debt accounts."""
    debts = db.query(DebtAccount).filter(DebtAccount.user_id == user.id).all()
    return debts


# ============ GOALS ============
@router.post("/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(
    goal_data: GoalCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Create a new financial goal."""
    goal = Goal(**goal_data.dict(), user_id=user.id)
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.get("/goals", response_model=List[GoalResponse])
def list_goals(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """List user's financial goals."""
    goals = db.query(Goal).filter(Goal.user_id == user.id).order_by(Goal.priority).all()
    return goals