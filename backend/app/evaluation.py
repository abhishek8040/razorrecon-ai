import os
from sqlmodel import Session, select
from typing import List
from app.models import Payment, Settlement, ReconciliationResult, EvaluationRun
from decimal import Decimal
import pandas as pd
import uuid

class EvaluationEngine:
    def __init__(self, session: Session):
        self.session = session
        
    def evaluate(self, run_id: str, dataset_name: str = "demo") -> EvaluationRun:
        # Fetch the results from the run
        results = self.session.exec(select(ReconciliationResult).where(ReconciliationResult.run_id == run_id)).all()
        
        # Determine ground truth from the CSV files used (assume it's the demo dataset)
        try:
            payments_df = pd.read_csv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", dataset_name, "payments.csv"))
            settlements_df = pd.read_csv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", dataset_name, "settlements.csv"))
        except FileNotFoundError:
            return None
            
        total_records = len(payments_df)
        correct_matches = 0
        incorrect_matches = 0
        unresolved_records = 0
        
        # Map ground truth: payment_id -> set of possible valid settlement ids (based on reference)
        ground_truth = {}
        for _, p in payments_df.iterrows():
            valid_settlements = settlements_df[settlements_df['reference'] == p['id']]['id'].tolist()
            ground_truth[p['id']] = valid_settlements
            
        for res in results:
            p_id = res.source_record_id
            matched_s_id = res.matched_record_id
            
            if res.result_type == "UNRESOLVED":
                unresolved_records += 1
                continue
                
            if matched_s_id in ground_truth.get(p_id, []):
                correct_matches += 1
            else:
                incorrect_matches += 1
                
        precision = correct_matches / (correct_matches + incorrect_matches) if (correct_matches + incorrect_matches) > 0 else 0
        recall = correct_matches / total_records if total_records > 0 else 0
        accuracy = correct_matches / total_records if total_records > 0 else 0
        
        eval_run = EvaluationRun(
            id=f"eval_{uuid.uuid4().hex[:12]}",
            dataset_name=dataset_name,
            dataset_type="HELDOUT" if dataset_name == "heldout" else "DEMO",
            total_records=total_records,
            correct_matches=correct_matches,
            incorrect_matches=incorrect_matches,
            unresolved_records=unresolved_records,
            precision=precision,
            recall=recall,
            accuracy=accuracy,
            auto_resolution_precision=precision # Simplified for hackathon
        )
        self.session.add(eval_run)
        self.session.commit()
        return eval_run
