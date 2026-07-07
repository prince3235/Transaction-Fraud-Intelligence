import json
import sqlite3
import sys
from pathlib import Path

# Ensure src module is in path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import simpleeval
from src.storage import get_db_path

def migrate_rules():
    db_path = get_db_path()
    if not db_path.exists():
        print("Database not found.")
        return

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    
    cur.execute("SELECT id, name, condition_json FROM business_rules")
    rules = cur.fetchall()
    
    class DummyDict(dict):
        def __getitem__(self, key):
            return 0
            
    dummy_features = DummyDict()
    evaluator = simpleeval.SimpleEval(names=dummy_features, functions={"abs": abs})
    
    for rule in rules:
        rule_id = rule["id"]
        name = rule["name"]
        condition = rule["condition_json"]
        
        # If it looks like JSON, try to convert it
        new_condition = condition
        needs_update = False
        
        try:
            parsed = json.loads(condition)
            if isinstance(parsed, dict) and "field" in parsed:
                field = parsed["field"]
                if "equals" in parsed:
                    new_condition = f"{field} == {parsed['equals']}"
                else:
                    op = parsed.get("operator", "==")
                    th = parsed.get("threshold", 0)
                    new_condition = f"{field} {op} {th}"
                needs_update = True
        except (json.JSONDecodeError, TypeError):
            # Already a string expression or invalid
            pass

        # Validate with simpleeval
        try:
            evaluator.eval(new_condition)
        except (simpleeval.InvalidExpression, SyntaxError) as e:
            print(f"FAILED (Syntax): Rule '{name}' [ID: {rule_id}] - '{new_condition}' -> {e}")
            continue
        except (simpleeval.NameNotDefined, simpleeval.FunctionNotDefined):
            pass # Valid syntax, just missing variables
        except Exception as e:
            print(f"FAILED (Unknown): Rule '{name}' [ID: {rule_id}] - '{new_condition}' -> {e}")
            continue
            
        if needs_update:
            print(f"MIGRATED: Rule '{name}' [ID: {rule_id}] converted to '{new_condition}'")
            cur.execute("UPDATE business_rules SET condition_json = ? WHERE id = ?", (new_condition, rule_id))
        else:
            print(f"OK: Rule '{name}' [ID: {rule_id}] is already a valid expression.")
            
    con.commit()
    con.close()

if __name__ == "__main__":
    migrate_rules()
