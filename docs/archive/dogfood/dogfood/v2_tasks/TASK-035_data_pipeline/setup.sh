#!/bin/bash
cd "$(dirname "$0")"
mkdir -p repo
cat > repo/pipeline.py << 'PYEOF'
class Pipeline:
    """Data transformation pipeline."""
    
    def __init__(self):
        self.steps = []
    
    def add_step(self, name, func):
        """Add a transformation step."""
        self.steps.append({"name": name, "func": func})
    
    def run(self, data):
        """Run all steps on data. Returns (result, report)."""
        report = {"steps": [], "errors": []}
        result = data
        
        for step in self.steps:
            try:
                result = step["func"](result)
                report["steps"].append({"name": step["name"], "status": "ok"})
            except Exception as e:
                report["steps"].append({"name": step["name"], "status": "error", "error": str(e)})
                report["errors"].append(str(e))
                # BUG: continues with UNCHANGED result after error
                # Should skip this step and continue with previous result
                # But actually the bug is: it continues with the OLD result
                # which might be wrong if a partial transformation happened
        
        report["success"] = len(report["errors"]) == 0
        return result, report
    
    def run_strict(self, data):
        """Run all steps. Stop on first error."""
        report = {"steps": [], "errors": []}
        result = data
        
        for step in self.steps:
            try:
                result = step["func"](result)
                report["steps"].append({"name": step["name"], "status": "ok"})
            except Exception as e:
                report["steps"].append({"name": step["name"], "status": "error", "error": str(e)})
                report["errors"].append(str(e))
                # BUG: doesn't actually stop — falls through to next step
                # Missing break/return
        
        report["success"] = len(report["errors"]) == 0
        return result, report
PYEOF

cat > repo/test_pipeline.py << 'PYEOF'
import sys
sys.path.insert(0, '.')
from pipeline import Pipeline

def test_normal_run():
    p = Pipeline()
    p.add_step("double", lambda x: [i*2 for i in x])
    p.add_step("filter", lambda x: [i for i in x if i > 4])
    
    result, report = p.run([1, 2, 3, 4, 5])
    assert result == [6, 8, 10], f"Got: {result}"
    assert report["success"] == True

def test_error_continues():
    """run() should skip failed step and continue with previous result."""
    p = Pipeline()
    p.add_step("step1", lambda x: x + [99])
    p.add_step("bad_step", lambda x: x / 0)  # Will fail
    p.add_step("step3", lambda x: x + [100])
    
    result, report = p.run([1])
    assert report["success"] == False
    assert len(report["errors"]) == 1
    # step1 adds 99, bad_step fails, step3 should add 100 to [1, 99]
    assert result == [1, 99, 100], f"Expected [1, 99, 100], got {result}"

def test_strict_stops():
    """run_strict() should stop on first error."""
    p = Pipeline()
    p.add_step("step1", lambda x: x + [99])
    p.add_step("bad_step", lambda x: x / 0)
    p.add_step("step3", lambda x: x + [100])
    
    result, report = p.run_strict([1])
    assert len(report["steps"]) == 2, f"Should stop after 2 steps, got {len(report['steps'])}"
    assert result == [1, 99], f"Expected [1, 99], got {result}"

if __name__ == "__main__":
    tests = [test_normal_run, test_error_continues, test_strict_stops]
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: {t.__name__}: {e}")
            sys.exit(1)
    print("ALL TESTS PASSED")
PYEOF
