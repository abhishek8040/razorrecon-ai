import sys
import os

eval_path = "backend/app/evaluation.py"
with open(eval_path, "r") as f:
    content = f.read()

content = content.replace('f"../data/{dataset_name}/payments.csv"', 'os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", dataset_name, "payments.csv")')
content = content.replace('f"../data/{dataset_name}/settlements.csv"', 'os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", dataset_name, "settlements.csv")')

if "import os" not in content:
    content = "import os\n" + content

with open(eval_path, "w") as f:
    f.write(content)
