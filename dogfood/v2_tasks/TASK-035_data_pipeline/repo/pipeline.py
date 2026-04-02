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
