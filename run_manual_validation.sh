#!/bin/bash
set -e

echo "1. Start clean database"
cd backend
rm -f razorrecon.db

echo "2. Load demo data"
source venv/bin/activate
export PYTHONPATH=.
python app/cli.py generate:data
python app/cli.py seed:db

echo "Starting server in background..."
python -m uvicorn app.main:app --port 8000 &
SERVER_PID=$!
sleep 3

echo "3. Run reconciliation"
curl -s -X POST http://127.0.0.1:8000/api/reconcile > /dev/null

echo "4. Verify dashboard metrics"
curl -s http://127.0.0.1:8000/api/metrics > metrics.json
cat metrics.json

echo "5. Get exceptions to find candidates for investigation"
curl -s http://127.0.0.1:8000/api/exceptions > exceptions.json
MISSING_BANK=$(cat exceptions.json | grep -o '"id":"[^"]*","exception_type":"MISSING_BANK_TRANSACTION"' | head -n 1 | cut -d'"' -f4)
AMBIGUOUS=$(cat exceptions.json | grep -o '"id":"[^"]*","exception_type":"AMBIGUOUS_BANK_MATCH"' | head -n 1 | cut -d'"' -f4)

echo "Missing bank exception: $MISSING_BANK"
echo "Ambiguous bank exception: $AMBIGUOUS"

if [ -n "$MISSING_BANK" ]; then
    echo "9. Run AI investigation"
    curl -s -X POST http://127.0.0.1:8000/api/exceptions/${MISSING_BANK}/investigate > ai_investigate.json
    cat ai_investigate.json
    
    echo "12. Resolve exception"
    curl -s -X POST http://127.0.0.1:8000/api/exceptions/${MISSING_BANK}/resolve -H "Content-Type: application/json" -d '{"notes": "Manual resolve"}' > /dev/null
fi

echo "18. Run reconciliation a second time"
curl -s -X POST http://127.0.0.1:8000/api/reconcile > /dev/null

echo "19. Verify no active metric inflation"
curl -s http://127.0.0.1:8000/api/metrics > metrics2.json
cat metrics2.json

echo "21. Run held-out evaluation"
curl -s -X POST http://127.0.0.1:8000/api/evaluate/heldout > evaluate.json
cat evaluate.json

kill $SERVER_PID
