import re

with open("backend/app/engine.py", "r") as f:
    content = f.read()

# Replace the constants at the top
content = re.sub(r'MAX_AMOUNT_TOLERANCE_PERCENT = Decimal\(os\.environ\.get\("MAX_AMOUNT_TOLERANCE_PERCENT", "2\.0"\)\)\n', "", content)
content = re.sub(r'MAX_TIME_WINDOW_DAYS = int\(os\.environ\.get\("MAX_TIME_WINDOW_DAYS", "5"\)\)\n', "", content)

# Import PolicyEngine
content = content.replace("from app.models import Payment, Settlement, BankTransaction, ReconciliationResult, ExceptionRecord, ReconciliationRun, EvaluationRun, Merchant", "from app.models import Payment, Settlement, BankTransaction, ReconciliationResult, ExceptionRecord, ReconciliationRun, EvaluationRun, Merchant\nfrom app.policy import PolicyEngine")

with open("backend/app/engine.py", "w") as f:
    f.write(content)
