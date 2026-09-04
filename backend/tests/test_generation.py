import os
import csv
import tempfile
from decimal import Decimal
from app.cli import generate_data

def test_deterministic_generation():
    """
    Test that running synthetic data generation twice with the same seed
    produces identical datasets.
    """
    import random
    
    # Generation 1
    random.seed(42)
    generate_data(num_records=50, is_demo=False)
    
    heldout_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "heldout")
    
    with open(os.path.join(heldout_dir, "payments.csv"), "r") as f:
        p1 = f.read()
    with open(os.path.join(heldout_dir, "settlements.csv"), "r") as f:
        s1 = f.read()
    with open(os.path.join(heldout_dir, "bank_transactions.csv"), "r") as f:
        b1 = f.read()
        
    # Generation 2
    random.seed(42)
    generate_data(num_records=50, is_demo=False)
    
    with open(os.path.join(heldout_dir, "payments.csv"), "r") as f:
        p2 = f.read()
    with open(os.path.join(heldout_dir, "settlements.csv"), "r") as f:
        s2 = f.read()
    with open(os.path.join(heldout_dir, "bank_transactions.csv"), "r") as f:
        b2 = f.read()
        
    assert p1 == p2, "Payments generation is not deterministic"
    assert s1 == s2, "Settlements generation is not deterministic"
    assert b1 == b2, "Bank transactions generation is not deterministic"
