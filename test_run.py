from borg.benchmarks.runner import BenchmarkRunner
from borg.benchmarks.report import print_summary

runner = BenchmarkRunner()
baseline, borg, report = runner.run_all()
print_summary(report)