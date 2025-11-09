"""Data import/export routes."""
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status
)
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    User,
    Expense,
    ExpenseType,
    DebtAccount,
    Goal,
    TransactionImport
)
from app.schemas import CSVUploadResponse, ExportResponse
from app.security import get_current_user
from app.services.audit import log_action
from app.services.imports import parse_bank_statement_csv, validate_csv_size
from app.settings import settings

router = APIRouter(prefix="/data", tags=["data"])

_FIXED_KEYWORDS = {
    "rent",
    "utility",
    "utilities",
    "internet",
    "phone",
    "insurance",
    "tuition",
    "school",
    "mortgage",
    "emi",
    "loan",
    "subscription"
}


def _infer_expense_type(category: str, description: str) -> ExpenseType:
    """Heuristically label imported expenses as fixed or variable."""
    text = f"{category} {description}".lower()
    for keyword in _FIXED_KEYWORDS:
        if keyword in text:
            return ExpenseType.FIXED
    return ExpenseType.VARIABLE


@router.post("/import-csv", response_model=CSVUploadResponse, status_code=status.HTTP_201_CREATED)
async def import_csv(
    file: UploadFile = File(...),
    has_header: bool = Form(True),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
) -> CSVUploadResponse:
    """Import a bank statement CSV and convert rows into expenses."""

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    contents = await file.read()

    try:
        validate_csv_size(len(contents), settings.MAX_CSV_SIZE_MB)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        transactions, category_totals = parse_bank_statement_csv(contents, has_header)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    rows_processed = len(transactions)
    expenses_added = 0

    for txn in transactions:
        amount = float(txn.get("amount", 0))
        if amount <= 0:
            continue

        description = txn.get("description") or "Imported Expense"
        category = txn.get("category") or "Uncategorized"

        expense = Expense(
            user_id=user.id,
            name=description[:255],
            amount=round(abs(amount), 2),
            type=_infer_expense_type(category, description)
        )
        db.add(expense)
        expenses_added += 1

    db.add(TransactionImport(
        user_id=user.id,
        csv_filename=file.filename,
        processed_count=rows_processed
    ))

    db.commit()

    log_action(
        db,
        "csv_imported",
        user,
        {
            "filename": file.filename,
            "rows_processed": rows_processed,
            "expenses_added": expenses_added,
            "categories": category_totals
        }
    )

    message = (
        f"Imported {expenses_added} expenses from {file.filename}. "
        "Please review entries for accuracy."
    )

    return CSVUploadResponse(
        filename=file.filename,
        rows_processed=rows_processed,
        expenses_added=expenses_added,
        message=message
    )


@router.get("/export", response_model=ExportResponse)
def export_data(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
) -> ExportResponse:
    """Export a snapshot of the user's finances."""

    expenses: List[Expense] = (
        db.query(Expense)
        .filter(Expense.user_id == user.id)
        .order_by(Expense.created_at.desc())
        .all()
    )
    debts: List[DebtAccount] = (
        db.query(DebtAccount)
        .filter(DebtAccount.user_id == user.id)
        .order_by(DebtAccount.start_date.desc())
        .all()
    )
    goals: List[Goal] = (
        db.query(Goal)
        .filter(Goal.user_id == user.id)
        .order_by(Goal.created_at.desc())
        .all()
    )

    return ExportResponse(
        expenses=expenses,
        debts=debts,
        goals=goals
    )