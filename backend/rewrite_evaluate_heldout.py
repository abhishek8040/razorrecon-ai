import re

with open("backend/app/main.py", "r") as f:
    content = f.read()

new_evaluate = """@app.post("/api/evaluate/heldout")
def evaluate_heldout(session: Session = Depends(get_session)):
    from sqlmodel import create_engine, Session as SQLSession, SQLModel
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    heldout_dir = os.path.join(project_root, "data", "heldout")
    
    try:
        # 1. Create a completely isolated in-memory DB for the engine run
        mem_engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(mem_engine)
        
        with SQLSession(mem_engine) as mem_session:
            payments_df = pd.read_csv(os.path.join(heldout_dir, "payments.csv"))
            settlements_df = pd.read_csv(os.path.join(heldout_dir, "settlements.csv"))
            bank_txs_df = pd.read_csv(os.path.join(heldout_dir, "bank_transactions.csv"))
            
            # Load heldout data temporarily
            for _, row in payments_df.iterrows():
                row_dict = row.to_dict()
                row_dict["payment_time"] = pd.to_datetime(row_dict["payment_time"]).to_pydatetime()
                mem_session.add(Payment(**row_dict))
                
            for _, row in settlements_df.iterrows():
                row_dict = row.to_dict()
                row_dict["settlement_time"] = pd.to_datetime(row_dict["settlement_time"]).to_pydatetime()
                mem_session.add(Settlement(**row_dict))
                
            for _, row in bank_txs_df.iterrows():
                row_dict = row.to_dict()
                row_dict["transaction_time"] = pd.to_datetime(row_dict["transaction_time"]).to_pydatetime()
                mem_session.add(BankTransaction(**row_dict))
                
            mem_session.commit()
            
            # Run reconciliation on isolated DB
            run_id = f"run_{uuid.uuid4().hex[:12]}"
            recon_engine = ReconciliationEngine(mem_session, run_id)
            run = recon_engine.run(None)
            
            # Run evaluation on isolated DB
            eval_engine = EvaluationEngine(mem_session)
            eval_run = eval_engine.evaluate(run.id, "heldout")
            
            # Copy evaluation run to the main DB
            main_eval_run = EvaluationRun(**eval_run.model_dump())
            session.add(main_eval_run)
            session.commit()
            
            return main_eval_run
            
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))"""

start_idx = content.find("@app.post(\"/api/evaluate/heldout\")")
end_idx = content.find("class QAQuery(BaseModel):")

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_evaluate + "\n\n" + content[end_idx:]

with open("backend/app/main.py", "w") as f:
    f.write(content)
