import os
import csv
import uuid
import random
from datetime import datetime, timedelta
from decimal import Decimal
import argparse

random.seed(42) # Deterministic generation

def generate_data(num_records=1000, is_demo=True):
    dataset_type = "demo" if is_demo else "heldout"
    output_dir = f"../data/{dataset_type}"
    os.makedirs(output_dir, exist_ok=True)
    
    payments = []
    settlements = []
    bank_transactions = []
    
    merchant_id = f"merch_{uuid.uuid4().hex[:8]}"
    start_date = datetime(2026, 1, 1)
    
    for i in range(num_records):
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"
        amount = Decimal(str(round(random.uniform(100.0, 50000.0), 2)))
        payment_time = start_date + timedelta(days=random.randint(0, 30), hours=random.randint(0, 23), minutes=random.randint(0, 59))
        
        payments.append({
            "id": payment_id,
            "external_id": payment_id,
            "merchant_id": merchant_id,
            "amount": amount,
            "currency": "INR",
            "payment_time": payment_time.isoformat(),
            "customer_reference": f"cust_{random.randint(1000, 9999)}",
            "order_reference": f"order_{random.randint(10000, 99999)}",
            "status": "captured",
            "metadata_json": "{}"
        })
        
        anomaly = random.random()
        # 60% exact match
        # 10% amount discrepancy
        # 8% missing settlement
        # 6% duplicate
        # 5% fee/tax mismatch (amount reduced by 2%)
        # 4% reference mismatch
        # 3% delayed settlement
        # 4% other
        
        settlement_id = f"setl_{uuid.uuid4().hex[:12]}"
        bank_txn_id = f"btxn_{uuid.uuid4().hex[:12]}"
        
        setl_amount = amount
        bank_amount = amount
        setl_time = payment_time + timedelta(days=1)
        bank_time = setl_time + timedelta(hours=2)
        setl_ref = payment_id
        
        skip_settlement = False
        duplicate = False
        
        if anomaly < 0.60:
            pass # exact match
        elif anomaly < 0.70:
            setl_amount = amount + Decimal("10.00") # Amount discrepancy
        elif anomaly < 0.78:
            skip_settlement = True
        elif anomaly < 0.84:
            duplicate = True
        elif anomaly < 0.89:
            setl_amount = round(amount * Decimal("0.98"), 2) # Fee mismatch
            bank_amount = setl_amount
        elif anomaly < 0.93:
            setl_ref = f"wrong_{payment_id}" # Reference mismatch
        elif anomaly < 0.96:
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
        with open(f"{output_dir}/{filename}", 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
                
    write_csv("payments.csv", payments, payments[0].keys() if payments else [])
    write_csv("settlements.csv", settlements, settlements[0].keys() if settlements else [])
    write_csv("bank_transactions.csv", bank_transactions, bank_transactions[0].keys() if bank_transactions else [])
    
    print(f"Generated {num_records} base records into {output_dir}")

def seed_db():
    from app.database import create_db_and_tables, engine
    from app.models import Merchant, Payment, Settlement, BankTransaction
    from sqlmodel import Session
    import pandas as pd
    
    create_db_and_tables()
    
    with Session(engine) as session:
        # Check if already seeded
        if session.query(Payment).first():
            print("Database already seeded.")
            return
            
        print("Seeding database...")
        # Read demo dataset
        payments_df = pd.read_csv("../data/demo/payments.csv")
        payments_df['payment_time'] = pd.to_datetime(payments_df['payment_time'])
        
        settlements_df = pd.read_csv("../data/demo/settlements.csv")
        settlements_df['settlement_time'] = pd.to_datetime(settlements_df['settlement_time'])
        
        bank_df = pd.read_csv("../data/demo/bank_transactions.csv")
        bank_df['transaction_time'] = pd.to_datetime(bank_df['transaction_time'])
        
        merchants_seen = set()
        
        for _, row in payments_df.iterrows():
            if row['merchant_id'] not in merchants_seen:
                session.add(Merchant(id=row['merchant_id'], name="Demo Merchant"))
                merchants_seen.add(row['merchant_id'])
            
            session.add(Payment(**row.to_dict()))
            
        for _, row in settlements_df.iterrows():
            session.add(Settlement(**row.to_dict()))
            
        for _, row in bank_df.iterrows():
            session.add(BankTransaction(**row.to_dict()))
            
        session.commit()
        print("Seeding complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["generate:data", "generate:heldout", "seed:db"])
    args = parser.parse_args()
    
    if args.command == "generate:data":
        generate_data(num_records=1000, is_demo=True)
    elif args.command == "generate:heldout":
        random.seed(99) # Different seed for heldout
        generate_data(num_records=500, is_demo=False)
    elif args.command == "seed:db":
        seed_db()
