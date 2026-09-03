import re

with open("backend/app/evaluation.py", "r") as f:
    content = f.read()

new_eval = """    def evaluate(self, run_id: str, dataset_name: str = "demo") -> EvaluationRun:
        # Fetch the results from the run
        results = self.session.exec(select(ReconciliationResult).where(ReconciliationResult.run_id == run_id)).all()
        
        # Determine ground truth from the CSV files used
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            payments_df = pd.read_csv(os.path.join(base_dir, "data", dataset_name, "payments.csv"))
            settlements_df = pd.read_csv(os.path.join(base_dir, "data", dataset_name, "settlements.csv"))
            bank_df = pd.read_csv(os.path.join(base_dir, "data", dataset_name, "bank_transactions.csv"))
        except FileNotFoundError:
            return None
            
        total_records = len(payments_df)
        
        # Build 3-way ground truth mapping
        # Payment -> (Valid Settlements, Valid Bank Tx for those settlements)
        # We assume one bank tx matches one settlement reference
        ground_truth = {}
        for _, p in payments_df.iterrows():
            valid_settlements = settlements_df[settlements_df['reference'] == p['id']]['id'].tolist()
            # valid bank txs for this payment are those that point to the payment OR the valid settlements
            valid_bank_refs = [p['id']] + valid_settlements
            valid_bank_txs = bank_df[bank_df['bank_reference'].isin(valid_bank_refs)]['id'].tolist()
            ground_truth[p['id']] = {
                "settlements": valid_settlements,
                "banks": valid_bank_txs
            }
            
        correct_matches = 0
        incorrect_matches = 0
        unresolved_records = 0
        
        settlement_correct_matches = 0
        bank_correct_matches = 0
        three_way_correct_matches = 0
        
        auto_correct_matches = 0
        auto_incorrect_matches = 0
        three_way_matches = 0 # 3-way predictions made
        
        for res in results:
            p_id = res.source_record_id
            matched_s_id = res.matched_record_id
            matched_b_id = res.bank_transaction_id
            
            if res.result_type == "UNRESOLVED":
                unresolved_records += 1
                continue
                
            p_truth = ground_truth.get(p_id, {"settlements": [], "banks": []})
            
            is_s_correct = matched_s_id in p_truth["settlements"]
            is_b_correct = (matched_b_id in p_truth["banks"]) if matched_b_id else False
            
            if is_s_correct:
                settlement_correct_matches += 1
                
            if is_b_correct:
                bank_correct_matches += 1
                
            if res.result_type == "MATCHED_3_WAY":
                three_way_matches += 1
                if is_s_correct and is_b_correct:
                    three_way_correct_matches += 1

            # Legacy total correct matches based on 3-way completion if it's supposed to be 3-way
            if is_s_correct and (res.result_type == "MATCHED_2_WAY" or (res.result_type == "MATCHED_3_WAY" and is_b_correct)):
                correct_matches += 1
                if res.decision_source == "DETERMINISTIC":
                    auto_correct_matches += 1
            else:
                incorrect_matches += 1
                if res.decision_source == "DETERMINISTIC":
                    auto_incorrect_matches += 1
                
        precision = correct_matches / (correct_matches + incorrect_matches) if (correct_matches + incorrect_matches) > 0 else 0.0
        recall = correct_matches / total_records if total_records > 0 else 0.0
        accuracy = correct_matches / total_records if total_records > 0 else 0.0
        
        three_way_precision = three_way_correct_matches / three_way_matches if three_way_matches > 0 else 0.0
        three_way_recall = three_way_correct_matches / total_records if total_records > 0 else 0.0
        
        auto_total = auto_correct_matches + auto_incorrect_matches
        auto_resolution_precision = auto_correct_matches / auto_total if auto_total > 0 else 0.0
        
        three_way_match_rate = three_way_matches / total_records if total_records > 0 else 0.0
        unresolved_rate = unresolved_records / total_records if total_records > 0 else 0.0
        
        # Get throughput from the run
        run_record = self.session.exec(select(ReconciliationRun).where(ReconciliationRun.id == run_id)).first()
        throughput = 0.0
        if run_record and run_record.processing_time_ms and run_record.processing_time_ms > 0:
            throughput = total_records / (run_record.processing_time_ms / 1000)
        
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
            settlement_correct_matches=settlement_correct_matches,
            bank_correct_matches=bank_correct_matches,
            three_way_precision=three_way_precision,
            three_way_recall=three_way_recall,
            auto_resolution_precision=auto_resolution_precision,
            three_way_match_rate=three_way_match_rate,
            unresolved_rate=unresolved_rate,
            throughput_records_per_second=throughput
        )
        self.session.add(eval_run)
        self.session.commit()
        return eval_run"""

start_idx = content.find("    def evaluate")
end_idx = content.find("        self.session.add(eval_run)\n        self.session.commit()\n        return eval_run")
end_idx = content.find("\n", end_idx + len("        return eval_run"))

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_eval + content[end_idx:]

with open("backend/app/evaluation.py", "w") as f:
    f.write(content)
