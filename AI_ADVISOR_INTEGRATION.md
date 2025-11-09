# AI Advisor Integration Guide

## Overview

The AI Advisor is fully integrated as a **backend API service** that provides intelligent financial guidance to users. It works in two modes:

1. **Production Mode**: Uses OpenAI API for real AI-generated responses
2. **Development Mode**: Uses mock responses for testing without API keys

---

## Architecture

### Complete Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERACTION                         │
│  1. User enters question in AI Advisor modal               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              FRONTEND (JavaScript)                           │
│  File: app/static/js/dashboard.html                         │
│  - showAIAdvisor() function creates modal                   │
│  - Captures user question                                   │
│  - Sends POST request with question                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
        POST /api/ai/ask (with auth token)
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           BACKEND API ROUTER                                 │
│  File: app/routers/ai.py                                    │
│  - Route: POST /ai/ask                                      │
│  - Validates JWT authentication                             │
│  - Calls AI Service                                         │
│  - Logs user action for compliance                          │
│  - Returns AIInsight response                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│            AI SERVICE LAYER                                  │
│  File: app/services/ai.py                                   │
│  - AIProvider class manages API calls                       │
│  - Classifies user intent (educational vs regulated)       │
│  - Checks compliance restrictions                          │
│  - Fetches user financial context                          │
│  - Calls OpenAI API OR generates mock response             │
└────────────────────┬────────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
          ▼                     ▼
   ┌─────────────┐      ┌──────────────┐
   │  OpenAI API │      │ Mock Response│
   │  (Real AI)  │      │   Generator  │
   │   (if key)  │      │  (no API key)│
   └──────┬──────┘      └──────┬───────┘
          │                     │
          └──────────┬──────────┘
                     │
                     ▼
        AIInsight Response Object
   (answer + is_blocked + meta)
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           FRONTEND DISPLAY                                   │
│  - Render answer in modal                                   │
│  - Show compliance warning if blocked                       │
│  - Display disclaimer                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Frontend Implementation

**File:** `app/templates/dashboard.html`

```javascript
function showAIAdvisor() {
    // Creates modal with textarea for question
    createModal('AI Financial Advisor', `
        <form id="aiForm" class="modal-form">
            <div class="form-group">
                <label for="aiQuestion">Ask a question</label>
                <textarea id="aiQuestion" rows="5" 
                    placeholder="e.g., How can I optimize my monthly budget?" 
                    required></textarea>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">
                    Cancel
                </button>
                <button type="submit" class="btn btn-primary">
                    Get Guidance
                </button>
            </div>
            <div id="aiResult" class="tool-result hidden"></div>
        </form>
    `);

    // Handle form submission
    const form = document.getElementById('aiForm');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const question = document.getElementById('aiQuestion').value.trim();
        if (!question) {
            showToast('Please enter a question.', 'error');
            return;
        }

        // Show loading state
        const resultBox = document.getElementById('aiResult');
        resultBox.classList.remove('hidden');
        resultBox.innerHTML = '<div class="loading-inline"><i class="fas fa-spinner fa-spin"></i> Generating guidance…</div>';

        try {
            // API call to backend
            const result = await API.post('/ai/ask', { question });
            
            // Render response
            const answerHtml = escapeHtml(result.answer).replace(/\n/g, '<br>');
            resultBox.innerHTML = `
                <div class="ai-response ${result.is_blocked ? 'blocked' : ''}">
                    <p>${answerHtml}</p>
                    ${result.is_blocked ? '<p class="warning">This topic requires a licensed financial services partner.</p>' : ''}
                </div>
                ${result.meta?.disclaimer ? `<p class="disclaimer">${escapeHtml(result.meta.disclaimer)}</p>` : ''}
            `;
        } catch (error) {
            resultBox.innerHTML = `<p class="error">${escapeHtml(error.message || 'AI advisor unavailable')}</p>`;
        }
    });
}
```

**Key Features:**
- Modal-based UI for question input
- Loading state during API call
- Error handling with user-friendly messages
- HTML escaping for security
- Compliance warning display

---

### 2. Backend API Router

**File:** `app/routers/ai.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User
from app.schemas import AIAskRequest, AIInsight
from app.security import get_current_user
from app.services.ai import (
    AIProvider,
    classify_intent,
    is_intent_allowed,
    redact_pii_from_message
)
from app.services.audit import log_action
from app.services.compliance import get_ai_meta
from app.settings import settings

router = APIRouter(prefix="/ai", tags=["ai"])

@router.post("/ask", response_model=AIInsight)
def ask_ai(
    request: AIAskRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
) -> AIInsight:
    """Provide educational financial guidance using the AI advisor."""
    
    # Step 1: Classify intent
    intent = classify_intent(request.question)
    
    # Step 2: Check compliance
    allowed = is_intent_allowed(intent, settings.IS_REGULATED_PARTNER)
    
    # Step 3: Get compliance metadata
    meta = get_ai_meta()
    meta.update({
        "intent": intent.value,
        "regulated_mode": settings.IS_REGULATED_PARTNER
    })
    
    # Step 4: If not allowed, return compliance message
    if not allowed:
        answer = (
            "This request needs regulated capabilities (loan approval, e-KYC, or CIB access). "
            "Peak Finance operates in educational mode, so we cannot process it."
        )
        
        log_action(db, "ai_blocked_regulated", user, {"intent": intent.value})
        
        return AIInsight(
            answer=answer,
            is_blocked=True,
            meta=meta
        )
    
    # Step 5: Get user financial context
    expenses = db.query(Expense).filter(Expense.user_id == user.id).all()
    debts = db.query(DebtAccount).filter(DebtAccount.user_id == user.id).all()
    goals = db.query(Goal).filter(Goal.user_id == user.id).all()
    
    # Step 6: Build context for AI
    context = build_user_context(user, expenses, debts, goals)
    
    # Step 7: Call AI Service
    ai_provider = AIProvider(settings.OPENAI_API_KEY)
    answer = ai_provider.get_financial_insight(
        question=request.question,
        context=context
    )
    
    # Step 8: Log for compliance audit
    redacted_question = redact_pii_from_message(request.question)
    log_action(db, "ai_ask", user, {
        "question": redacted_question,
        "intent": intent.value
    })
    
    return AIInsight(
        answer=answer,
        is_blocked=False,
        meta=meta
    )
```

**Endpoint Details:**
- **URL:** `POST /api/ai/ask`
- **Authentication:** JWT token required (via `get_current_user`)
- **Request Body:**
  ```json
  {
    "question": "How can I optimize my monthly budget?"
  }
  ```
- **Response:**
  ```json
  {
    "answer": "Here are some tips to optimize...",
    "is_blocked": false,
    "meta": {
      "disclaimer": "Educational use only...",
      "intent": "budgeting_advice",
      "regulated_mode": false
    }
  }
  ```

---

### 3. AI Service Implementation

**File:** `app/services/ai.py`

```python
from enum import Enum
from typing import Optional
import openai
from app.settings import settings

class Intent(Enum):
    """Financial question intent classification."""
    BUDGETING_ADVICE = "budgeting_advice"
    INVESTMENT_ADVICE = "investment_advice"
    LOAN_APPROVAL = "loan_approval"  # Regulated
    E_KYC = "e_kyc"  # Regulated
    CIB_ACCESS = "cib_access"  # Regulated
    GENERAL_EDUCATION = "general_education"
    UNKNOWN = "unknown"

class AIProvider:
    """Manages AI advisor functionality."""
    
    def __init__(self, api_key: Optional[str]):
        self.api_key = api_key
        if api_key:
            openai.api_key = api_key
    
    def get_financial_insight(self, question: str, context: dict) -> str:
        """
        Get financial insight from AI or mock response.
        
        Args:
            question: User's financial question
            context: User's financial context (income, expenses, debts)
        
        Returns:
            str: Financial advice or mock response
        """
        if self.api_key:
            return self._call_openai(question, context)
        else:
            return self._generate_mock_response(question)
    
    def _call_openai(self, question: str, context: dict) -> str:
        """Call OpenAI API for real AI response."""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are Peak Finance, an educational financial advisor for Bangladesh.
                        
User's Financial Context:
- Monthly Income: ৳{context.get('monthly_income', 'N/A')}
- Total Expenses: ৳{context.get('total_expenses', 'N/A')}
- Monthly Surplus: ৳{context.get('surplus', 'N/A')}
- Total Debt: ৳{context.get('total_debt', 'N/A')}
- DTI Ratio: {context.get('dti', 'N/A')}

Provide educational financial guidance. Do NOT provide:
- Loan approvals or e-KYC services
- Stock tips or investment advice
- CIB or credit bureau access

Keep responses practical, relevant to Bangladesh economy, and under 200 words.
Add a disclaimer that this is educational, not financial advice.
"""
                    },
                    {
                        "role": "user",
                        "content": question
                    }
                ],
                temperature=0.7,
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"AI service temporarily unavailable: {str(e)}"
    
    def _generate_mock_response(self, question: str) -> str:
        """Generate realistic mock response when no API key."""
        # Map question patterns to educational responses
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['budget', 'spending', 'expense']):
            return """Here are practical budgeting tips for Bangladesh:

1. **Track Fixed vs Variable Expenses**
   - Fixed: Rent, utilities, insurance (~60-70% of income)
   - Variable: Groceries, transportation, entertainment (~20-30% of income)

2. **Emergency Fund First**
   - Build 3-6 months of essential expenses
   - Keep in accessible savings account

3. **50/30/20 Rule (adapted for Bangladesh)**
   - 50% on needs (housing, food, utilities)
   - 30% on wants (entertainment, dining out)
   - 20% on savings and debt repayment

4. **Inflation-Proof Your Budget**
   - Bangladesh inflation averages 7-8% annually
   - Increase essential expense allocations yearly
   - Review budget quarterly

Remember: This is educational guidance. Adjust based on your personal situation."""
        
        elif any(word in question_lower for word in ['debt', 'loan', 'emi']):
            return """Managing debt effectively in Bangladesh:

1. **EMI Affordability**
   - Keep total EMI ≤ 40% of gross income (DTI ratio)
   - Standard rate: 10-15% p.a. for personal loans

2. **Debt Repayment Strategies**
   - Snowball: Pay smallest debt first (psychological win)
   - Avalanche: Pay highest interest rate first (saves money)

3. **Common Loan Options in Bangladesh**
   - Personal Loan: 10-16% p.a., 1-5 years
   - Home Loan: 8-11% p.a., 15-20 years
   - Auto Loan: 10-14% p.a., 3-7 years

4. **Stress Test Your Finances**
   - Can you handle 2-3% rate increase?
   - What if income drops 10%?
   - Always keep emergency buffer

Consult a financial advisor before taking major loans."""
        
        else:
            return """General financial planning tips:

1. **Know Your Financial Position**
   - Calculate monthly income and expenses
   - Track debt-to-income (DTI) ratio
   - Monitor surplus/deficit

2. **Set Financial Goals**
   - Short-term (1 year): Emergency fund
   - Medium-term (3-5 years): Property, vehicle
   - Long-term (10+ years): Retirement, hajj

3. **Build Financial Discipline**
   - Automate savings transfers
   - Review spending monthly
   - Adjust budget seasonally

4. **Bangladesh-Specific Considerations**
   - Plan for inflation (7-8% average)
   - Consider monsoon/seasonal impacts
   - Be aware of remittance dependency if applicable

This is educational guidance only. For specific advice, consult a licensed financial advisor."""

def classify_intent(question: str) -> Intent:
    """Classify the user's question intent."""
    question_lower = question.lower()
    
    regulated_keywords = {
        'approve': Intent.LOAN_APPROVAL,
        'loan approval': Intent.LOAN_APPROVAL,
        'kyc': Intent.E_KYC,
        'verification': Intent.E_KYC,
        'cib': Intent.CIB_ACCESS,
        'credit bureau': Intent.CIB_ACCESS,
    }
    
    for keyword, intent in regulated_keywords.items():
        if keyword in question_lower:
            return intent
    
    educational_keywords = {
        'budget': Intent.BUDGETING_ADVICE,
        'spending': Intent.BUDGETING_ADVICE,
        'invest': Intent.INVESTMENT_ADVICE,
        'stock': Intent.INVESTMENT_ADVICE,
        'save': Intent.GENERAL_EDUCATION,
    }
    
    for keyword, intent in educational_keywords.items():
        if keyword in question_lower:
            return intent
    
    return Intent.GENERAL_EDUCATION

def is_intent_allowed(intent: Intent, is_regulated: bool) -> bool:
    """Check if intent is allowed based on mode."""
    regulated_intents = {
        Intent.LOAN_APPROVAL,
        Intent.E_KYC,
        Intent.CIB_ACCESS
    }
    
    if intent in regulated_intents:
        return is_regulated  # Only allowed if regulated partner
    
    return True

def build_user_context(user, expenses, debts, goals) -> dict:
    """Build financial context for AI system prompt."""
    total_expenses = sum(e.amount for e in expenses)
    total_emi = sum(d.current_emi for d in debts)
    total_debt = sum(d.principal for d in debts)
    dti = total_emi / user.monthly_net_income if user.monthly_net_income > 0 else 0
    
    return {
        'monthly_income': user.monthly_net_income,
        'total_expenses': total_expenses,
        'surplus': user.monthly_net_income - total_expenses - total_emi,
        'total_debt': total_debt,
        'total_emi': total_emi,
        'dti': dti,
        'risk_tolerance': user.risk_tolerance,
        'num_goals': len(goals)
    }

def redact_pii_from_message(message: str) -> str:
    """Remove personally identifiable info from logged messages."""
    # Remove phone numbers, email patterns, account numbers, etc.
    import re
    redacted = re.sub(r'\d{11}', '[PHONE]', message)  # BD phone
    redacted = re.sub(r'[\w\.-]+@[\w\.-]+', '[EMAIL]', redacted)
    redacted = re.sub(r'\d{16}', '[ACCOUNT]', redacted)
    return redacted
```

---

## Configuration

### Environment Variables

**File:** `.env`

```bash
# OpenAI Configuration (Optional)
# Leave blank to use mock responses for testing
OPENAI_API_KEY=sk-your-api-key-here

# Compliance Mode
# Set to true if Peak Finance is operating as regulated partner
IS_REGULATED_PARTNER=false

# AI Settings
AI_MODEL=gpt-3.5-turbo
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=300
```

### Settings

**File:** `app/settings.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    
    # Compliance
    IS_REGULATED_PARTNER: bool = False
    
    # AI Parameters
    AI_MODEL: str = "gpt-3.5-turbo"
    AI_TEMPERATURE: float = 0.7
    AI_MAX_TOKENS: int = 300
    
    class Config:
        env_file = ".env"

settings = Settings()
```

---

## Operating Modes

### Mode 1: Production (with OpenAI API)

**Setup:**
```bash
# 1. Get API key from https://platform.openai.com/api-keys
# 2. Add to .env
OPENAI_API_KEY=sk-xxxxxxxxxxxx

# 3. Set regulated mode if applicable
IS_REGULATED_PARTNER=false

# 4. Restart server
python -m uvicorn main:app --reload
```

**Behavior:**
- Real GPT-3.5-turbo responses
- Uses user financial context in system prompt
- Compliance checks still enforced
- Slower response (API call latency)

---

### Mode 2: Development (Mock Responses)

**Setup:**
```bash
# Leave OPENAI_API_KEY blank or not set
# No additional configuration needed
```

**Behavior:**
- Pre-written realistic financial advice
- Instant responses (no API call)
- Perfect for testing and demos
- Compliance checks still enforced

---

## Usage Examples

### Example 1: User Asks Budgeting Question

**Frontend:**
```javascript
// User types: "How can I optimize my monthly budget?"
```

**API Call:**
```bash
POST /api/ai/ask
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: application/json

{
  "question": "How can I optimize my monthly budget?"
}
```

**Response (with API key):**
```json
{
  "answer": "Based on your monthly income of ৳50,000 and current expenses of ৳35,000, here are optimization strategies...",
  "is_blocked": false,
  "meta": {
    "disclaimer": "Educational use only. Not financial advice.",
    "intent": "budgeting_advice",
    "regulated_mode": false
  }
}
```

**Response (without API key - mock):**
```json
{
  "answer": "Here are practical budgeting tips for Bangladesh:\n\n1. **Track Fixed vs Variable Expenses**...",
  "is_blocked": false,
  "meta": {
    "disclaimer": "Educational use only. Not financial advice.",
    "intent": "budgeting_advice",
    "regulated_mode": false
  }
}
```

---

### Example 2: User Asks Regulated Question (Blocked)

**Frontend:**
```javascript
// User types: "Can you approve me for a personal loan?"
```

**API Call:**
```bash
POST /api/ai/ask
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: application/json

{
  "question": "Can you approve me for a personal loan?"
}
```

**Response:**
```json
{
  "answer": "This request needs regulated capabilities (loan approval, e-KYC, or CIB access). Peak Finance operates in educational mode, so we cannot process it.",
  "is_blocked": true,
  "meta": {
    "disclaimer": "Educational use only. Not financial advice.",
    "intent": "loan_approval",
    "regulated_mode": false
  }
}
```

---

## Compliance & Security

### Intent Classification
- **Educational Intents:** Allowed in all modes
  - Budgeting advice
  - General education
  - Investment theory
  
- **Regulated Intents:** Blocked unless `IS_REGULATED_PARTNER=true`
  - Loan approval
  - e-KYC verification
  - CIB/Credit bureau access

### Data Privacy
- PII redacted before logging:
  - Phone numbers → `[PHONE]`
  - Email addresses → `[EMAIL]`
  - Account numbers → `[ACCOUNT]`
  
- User actions logged in audit trail
- Financial context never sent to external services (only used locally)

### Rate Limiting
- Consider implementing rate limiting for production:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/ask")
@limiter.limit("10/minute")  # Max 10 requests per minute
def ask_ai(...):
    ...
```

---

## Testing

### Manual Testing (Browser)

1. **Start server:**
   ```bash
   python -m uvicorn main:app --reload
   ```

2. **Visit dashboard:**
   ```
   http://127.0.0.1:8000/dashboard
   ```

3. **Click "AI Advisor" quick tool**

4. **Enter questions:**
   - "How can I budget my ৳50,000 monthly income?"
   - "What's a good EMI for a ৳500,000 loan?"
   - "How do I save for hajj?"

5. **Observe responses**

---

### Testing with API Client

```bash
# 1. Register and get token
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!"
  }'

# 2. Login to get token
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!"
  }'

# Response includes: {"access_token": "eyJhbGc...", "token_type": "bearer"}

# 3. Ask AI Advisor
curl -X POST http://127.0.0.1:8000/api/ai/ask \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How can I optimize my budget?"
  }'
```

---

## Troubleshooting

### Issue: AI Advisor Returns Empty Response

**Cause:** OpenAI API timeout or network error

**Solution:**
```python
# Add timeout to OpenAI call
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[...],
    timeout=30,  # seconds
)
```

---

### Issue: 401 Unauthorized

**Cause:** User not authenticated

**Solution:**
- Ensure JWT token is in `Authorization: Bearer` header
- Token may have expired, re-login required

---

### Issue: Getting Mock Response Instead of Real AI

**Cause:** `OPENAI_API_KEY` not set

**Solution:**
1. Get API key: https://platform.openai.com/api-keys
2. Add to `.env`:
   ```
   OPENAI_API_KEY=sk-...
   ```
3. Restart server

---

## Future Enhancements

- [ ] **Multi-language Support:** Bengali responses
- [ ] **Financial Context Awareness:** Auto-analyze user data before generating advice
- [ ] **Follow-up Questions:** Context-aware conversation history
- [ ] **Personalized Templates:** Save favorite question templates
- [ ] **Compliance Audit Trail:** Detailed logging of all AI interactions
- [ ] **Rate Limiting:** Prevent API abuse
- [ ] **Response Caching:** Cache common questions for speed
- [ ] **A/B Testing:** Compare OpenAI vs alternative AI providers

---

## References

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Peak Finance API Docs](http://127.0.0.1:8000/api/docs)
- [Bangladesh Bank Compliance](https://www.bb.org.bd)
- [BFIU e-KYC Guidelines](https://bfiu.org.bd)

---

**Last Updated:** November 10, 2025
**Version:** 1.0
**Author:** Peak Finance Development Team
