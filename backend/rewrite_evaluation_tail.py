with open("backend/app/evaluation.py", "r") as f:
    content = f.read()

content = content.replace("""        self.session.add(eval_run)
        self.session.commit()
        self.session.refresh(eval_run)
        return eval_run
        self.session.commit()
        return eval_run""", """        self.session.add(eval_run)
        self.session.commit()
        self.session.refresh(eval_run)
        return eval_run""")

with open("backend/app/evaluation.py", "w") as f:
    f.write(content)
