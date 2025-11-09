"""Compliance utilities and disclaimers."""
from typing import Dict

# Educational disclaimer for all financial calculations
CALC_DISCLAIMER = (
    "Educational estimates only; not financial advice. "
    "Actual results may vary based on individual circumstances."
)

# Loan-specific disclaimer
LOAN_DISCLAIMER = (
    "Loan estimates are illustrative; approval and terms are set solely by licensed lenders. "
    "This is not a loan offer or commitment."
)

# AI-specific disclaimer
AI_DISCLAIMER = (
    "AI answers are generated from your inputs; verify before acting. "
    "This is educational guidance, not professional financial advice."
)

# Projection disclaimer
PROJECTION_DISCLAIMER = (
    "Projections are estimates and may differ from real prices. "
    "Market conditions and inflation rates vary."
)

# Footer compliance text (HTML)
FOOTER_COMPLIANCE_HTML = """
<div class="text-xs text-gray-600 space-y-2">
    <p><strong>Important Disclaimer:</strong> Peak Finance is an educational tool only. 
    We do not provide financial advice, loan approvals, e-KYC services, or access to credit information bureaus (CIB).</p>
    
    <p>All calculations, projections, and AI responses are for informational purposes only. 
    Please consult licensed financial professionals for personalized advice.</p>
    
    <p><strong>Regulatory References (Bangladesh):</strong></p>
    <ul class="list-disc list-inside ml-4">
        <li><a href="https://bfiu.org.bd/pdf/regulationguideline/aml/jan082020_ekyc.pdf" 
               target="_blank" rel="noopener" class="underline hover:text-blue-600">
               BFIU e-KYC Guideline</a></li>
        <li><a href="https://www.bb.org.bd/mediaroom/circulars/aml/jan082020bfiu25.pdf" 
               target="_blank" rel="noopener" class="underline hover:text-blue-600">
               Bangladesh Bank AML Circular</a></li>
        <li><a href="https://www.fatf-gafi.org/en/countries/detail/Bangladesh.html" 
               target="_blank" rel="noopener" class="underline hover:text-blue-600">
               FATF Bangladesh</a></li>
    </ul>
    
    <p class="mt-2">If regulated features are enabled in the future, all operations will be conducted 
    through licensed partners in full compliance with BFIU e-KYC and AML/CFT requirements.</p>
</div>
"""


def get_calc_meta() -> Dict[str, str]:
    """Get metadata dict with calculation disclaimer."""
    return {"disclaimer": CALC_DISCLAIMER}


def get_loan_meta() -> Dict[str, str]:
    """Get metadata dict with loan disclaimer."""
    return {"disclaimer": f"{CALC_DISCLAIMER} {LOAN_DISCLAIMER}"}


def get_ai_meta() -> Dict[str, str]:
    """Get metadata dict with AI disclaimer."""
    return {"disclaimer": AI_DISCLAIMER}


def get_projection_meta() -> Dict[str, str]:
    """Get metadata dict with projection disclaimer."""
    return {"disclaimer": f"{CALC_DISCLAIMER} {PROJECTION_DISCLAIMER}"}


def check_regulated_feature(is_regulated: bool, feature_name: str) -> None:
    """
    Check if a regulated feature is allowed.
    
    Args:
        is_regulated: Whether app is in regulated mode
        feature_name: Name of the feature being checked
        
    Raises:
        PermissionError: If feature is not allowed
    """
    if not is_regulated:
        raise PermissionError(
            f"{feature_name} is not available in educational mode. "
            "This feature requires a licensed financial services partner. "
            "Please contact support for information about regulated services."
        )