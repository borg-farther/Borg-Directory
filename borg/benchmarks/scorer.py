"""
Task scorer for evaluating benchmark results.
Uses keyword pattern matching to deterministically score task solutions.
"""

from dataclasses import dataclass
from typing import Optional

from borg.benchmarks.tasks import Task


@dataclass
class TaskScore:
    """Result of scoring a task solution."""

    solved: bool  # Was the task successfully solved?
    time_seconds: float  # How long did it take (simulated)
    quality: int  # 0-10 quality score
    used_best_practice: bool  # Did the approach use best practices?
    hit_anti_pattern: bool  # Did the approach use known anti-patterns?
    reasoning: str  # Human-readable explanation of the score


class TaskScorer:
    """
    Scores task solutions based on keyword matching against the task rubric.

    Scoring logic:
    - Quality 10: rubric keywords found, no anti-pattern keywords
    - Quality 7: rubric keywords found, but some anti-pattern keywords
    - Quality 4: partial rubric coverage
    - Quality 0: anti-pattern keywords dominate or wrong approach
    - Solved: True if quality >= 4
    """

    def score(self, task: Task, result: "TaskResult") -> TaskScore:
        """
        Score a task result against a task's rubric.

        Args:
            task: The task being evaluated
            result: The result from running the task (contains solution text)

        Returns:
            TaskScore with detailed scoring breakdown
        """
        solution = result.solution.lower()
        rubric_keywords = [k.lower() for k in task.rubric]
        anti_pattern_keywords = [k.lower() for k in task.anti_patterns]

        # Count rubric keyword matches
        rubric_matches = self._count_matches(solution, rubric_keywords)
        rubric_coverage = rubric_matches / len(rubric_keywords) if rubric_keywords else 0

        # Count anti-pattern keyword matches
        anti_pattern_matches = self._count_matches(solution, anti_pattern_keywords)
        anti_pattern_density = (
            anti_pattern_matches / len(anti_pattern_keywords) if anti_pattern_keywords else 0
        )

        # Calculate quality score
        quality = self._calculate_quality(
            rubric_coverage, anti_pattern_density, rubric_matches, anti_pattern_matches
        )

        # Determine if solved (quality >= 4)
        solved = quality >= 4

        # Check best practice usage
        used_best_practice = rubric_coverage >= 0.3 and anti_pattern_density < 0.2

        # Check if anti-pattern was hit
        hit_anti_pattern = anti_pattern_density >= 0.10

        # Generate reasoning
        reasoning = self._generate_reasoning(
            task, rubric_coverage, anti_pattern_density, rubric_matches, anti_pattern_matches, quality
        )

        return TaskScore(
            solved=solved,
            time_seconds=result.time_seconds,
            quality=quality,
            used_best_practice=used_best_practice,
            hit_anti_pattern=hit_anti_pattern,
            reasoning=reasoning,
        )

    def _count_matches(self, text: str, keywords: list[str]) -> int:
        """Count how many keywords appear in the text."""
        if not keywords:
            return 0
        matches = 0
        for keyword in keywords:
            # Handle multi-word phrases
            if keyword in text:
                matches += 1
        return matches

    def _calculate_quality(
        self,
        rubric_coverage: float,
        anti_pattern_density: float,
        rubric_matches: int,
        anti_pattern_matches: int,
    ) -> int:
        """
        Calculate quality score 0-10 based on rubric coverage and anti-pattern density.

        Quality rubric:
        - 10: optimal approach (high rubric coverage, no anti-patterns)
        - 7: correct but suboptimal (rubric covered but some anti-patterns)
        - 4: partially solved (partial rubric coverage)
        - 0: wrong approach (low rubric coverage OR high anti-pattern density)
        """
        # Base quality on rubric coverage
        if rubric_coverage >= 0.6 and anti_pattern_density < 0.2:
            return 10
        elif rubric_coverage >= 0.5 and anti_pattern_density < 0.3:
            return 9
        elif rubric_coverage >= 0.4 and anti_pattern_density < 0.3:
            return 8
        elif rubric_coverage >= 0.4 and anti_pattern_density >= 0.3:
            return 7
        elif rubric_coverage >= 0.3:
            return 7
        elif rubric_coverage >= 0.2:
            return 6
        elif rubric_coverage >= 0.15:
            return 5
        elif rubric_coverage >= 0.1:
            return 4
        elif rubric_matches > 0:
            return 3
        else:
            return 0

    def _generate_reasoning(
        self,
        task: Task,
        rubric_coverage: float,
        anti_pattern_density: float,
        rubric_matches: int,
        anti_pattern_matches: int,
        quality: int,
    ) -> str:
        """Generate human-readable explanation of the score."""
        reasons = []

        reasons.append(f"Rubric coverage: {rubric_matches}/{len(task.rubric)} keywords found ({rubric_coverage:.0%})")

        if task.anti_patterns:
            reasons.append(
                f"Anti-pattern hits: {anti_pattern_matches}/{len(task.anti_patterns)} ({anti_pattern_density:.0%})"
            )

        if quality == 10:
            reasons.append("Optimal solution - followed best practices")
        elif quality >= 7:
            reasons.append("Correct approach but could be improved")
        elif quality >= 4:
            reasons.append("Partially solved - key aspects missing")
        else:
            reasons.append("Wrong approach - anti-patterns or missing key concepts")

        return ". ".join(reasons)


# Import here to avoid circular reference
from borg.benchmarks.runner import TaskResult
