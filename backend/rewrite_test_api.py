with open("backend/tests/test_api.py", "r") as f:
    content = f.read()
    
content = content.replace('data["decision"]', 'data["investigation"]["decision"]')
content = content.replace('data["reason_codes"]', 'data["investigation"]["reason_codes"]')

with open("backend/tests/test_api.py", "w") as f:
    f.write(content)
