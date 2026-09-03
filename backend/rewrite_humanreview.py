import re

with open("backend/app/main.py", "r") as f:
    content = f.read()

new_content = """class HumanReview(BaseModel):
    notes: Optional[str] = None
    
@app.post("/api/exceptions/{exception_id}/resolve")"""

content = content.replace("@app.post(\"/api/exceptions/{exception_id}/resolve\")", new_content)

with open("backend/app/main.py", "w") as f:
    f.write(content)
