"""CSV import parsing and processing."""
import csv
import io
from typing import Dict, List, Tuple
from datetime import datetime


def parse_bank_statement_csv(
    file_content: bytes,
    has_header: bool = True
) -> Tuple[List[Dict[str, str]], Dict[str, float]]:
    """
    Parse bank statement CSV.
    
    Expected columns: date, description, category (optional), amount
    
    Args:
        file_content: CSV file bytes
        has_header: Whether first row is header
        
    Returns:
        Tuple of (transactions list, category totals dict)
    """
    try:
        # Decode with UTF-8, fallback to UTF-8-SIG for BOM
        try:
            content = file_content.decode('utf-8')
        except UnicodeDecodeError:
            content = file_content.decode('utf-8-sig')
        
        reader = csv.DictReader(io.StringIO(content))
        
        transactions = []
        category_totals: Dict[str, float] = {}
        
        for row in reader:
            # Normalize keys
            row = {k.strip().lower(): v.strip() for k, v in row.items()}
            
            # Extract fields
            date_str = row.get('date', '')
            description = row.get('description', 'Unknown')
            category = row.get('category', 'Uncategorized')
            amount_str = row.get('amount', '0')
            
            # Parse amount
            try:
                # Remove currency symbols and commas
                amount_clean = amount_str.replace('৳', '').replace(',', '').strip()
                amount = float(amount_clean)
            except ValueError:
                amount = 0.0
            
            transaction = {
                'date': date_str,
                'description': description,
                'category': category,
                'amount': amount
            }
            
            transactions.append(transaction)
            
            # Aggregate by category
            if category not in category_totals:
                category_totals[category] = 0.0
            category_totals[category] += amount
        
        return transactions, category_totals
    
    except Exception as e:
        raise ValueError(f"Failed to parse CSV: {str(e)}")


def validate_csv_size(file_size: int, max_size_mb: int = 5) -> None:
    """
    Validate CSV file size.
    
    Args:
        file_size: File size in bytes
        max_size_mb: Maximum allowed size in MB
        
    Raises:
        ValueError: If file exceeds size limit
    """
    max_bytes = max_size_mb * 1024 * 1024
    if file_size > max_bytes:
        raise ValueError(f"File size exceeds {max_size_mb}MB limit")