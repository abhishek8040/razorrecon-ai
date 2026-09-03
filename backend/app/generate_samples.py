import os
import csv
import uuid
import random
from datetime import datetime, timedelta
from decimal import Decimal

def generate_sample_batch(batch_number, num_records=100):
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "sampledata")
    os.makedirs(output_dir, exist_ok=True)
    
    payments = []
    settlements = []
    bank_transactions = []
    
    merchant_id = f"merch_custom_{batch_number}"
    start_date = datetime(2026, 2, 1) + timedelta(days=batch_number*10)
    
    for i in range(num_records):
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"
        amount = Decimal(str(round(random.uniform(10.0, 5000.0), 2)))
        payment_time = start_date + timedelta(days=random.randint(0, 5), hours=random.randint(0, 23), minutes=random.randint(0, 59))
        
        payments.append({
            "id": payment_id,
            "external_id": payment_id,
            "merchant_id": merchant_id,
            "amount": amount,
            "currency": "INR",
            "payment_time": payment_time.isoformat(),
            "customer_reference": f"cust_{random.randint(100, 999)}",
            "order_reference": f"order_{random.randint(1000, 9999)}",
            "status": "captured",
            "metadata_json": "{}"
        })
        
        anomaly = random.random()
        
        settlement_id = f"setl_{uuid.uuid4().hex[:12]}"
        bank_txn_id = f"btxn_{uuid.uuid4().hex[:12]}"
        
        setl_amount = amount
        bank_amount = amount
        setl_time = payment_time + timedelta(days=1)
        bank_time = setl_time + timedelta(hours=2)
        setl_ref = payment_id
        
        skip_settlement = False
        duplicate = False
        
        if anomaly < 0.70:
            pass # exact match
        elif anomaly < 0.75:
            setl_amount = amount + Decimal("10.00") # Amount discrepancy
        elif anomaly < 0.80:
            skip_settlement = True
        elif anomaly < 0.85:
            duplicate = True
        elif anomaly < 0.90:
            setl_amount = round(amount * Decimal("0.98"), 2) # Fee mismatch
            bank_amount = setl_amount
        elif anomaly < 0.95:
            setl_ref = f"wrong_{payment_id}" # Reference mismatch
        elif anomaly < 0.98:
            setl_time = payment_time + timedelta(days=5) # Delayed
        else:
            setl_amount = round(amount * Decimal("0.5"), 2) # Partial
        
        if not skip_settlement:
            settlements.append({
                "id": settlement_id,
                "external_id": settlement_id,
                "merchant_id": merchant_id,
                "settlement_amount": setl_amount,
                "settlement_time": setl_time.isoformat(),
                "reference": setl_ref,
                "status": "processed",
                "metadata_json": "{}"
            })
            
            bank_transactions.append({
                "id": bank_txn_id,
                "external_id": bank_txn_id,
                "merchant_id": merchant_id,
                "amount": bank_amount,
                "transaction_time": bank_time.isoformat(),
                "bank_reference": setl_ref,
                "description": f"Settlement {settlement_id}",
                "type": "CREDIT",
                "metadata_json": "{}"
            })
            
            if duplicate:
                settlements.append({
                    "id": f"{settlement_id}_dup",
                    "external_id": f"{settlement_id}_dup",
                    "merchant_id": merchant_id,
                    "settlement_amount": setl_amount,
                    "settlement_time": setl_time.isoformat(),
                    "reference": setl_ref,
                    "status": "processed",
                    "metadata_json": "{}"
                })
    
    def write_csv(filename, data, fieldnames):
        with open(os.path.join(output_dir, filename), 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
                
    write_csv(f"payment_{batch_number}.csv", payments, payments[0].keys() if payments else [])
    write_csv(f"settlement_{batch_number}.csv", settlements, settlements[0].keys() if settlements else [])
    write_csv(f"bank_{batch_number}.csv", bank_transactions, bank_transactions[0].keys() if bank_transactions else [])
    
    print(f"Generated batch {batch_number} into {output_dir}")

if __name__ == "__main__":
    random.seed(123)
    for i in range(1, 4):
        generate_sample_batch(i, num_records=200)
    print("Done!")
