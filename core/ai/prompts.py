import json
from typing import List, Dict, Any

class TreeOfThoughtPrompt:
    """
    Implements the Tree of Thoughts (ToT) prompting strategy.
    Encourages the LLM to explore multiple reasoning paths (thoughts),
    evaluate them, and backtrack if necessary.
    """

    @staticmethod
    def generate_thoughts(problem_statement: str, n_thoughts: int = 3) -> str:
        """
        Generates a prompt to produce multiple distinct initial thoughts.
        """
        prompt = f"""
You are an expert AI problem solver. I want you to use the "Tree of Thoughts" method to solve the following problem.
PROBLEM: {problem_statement}

Step 1: BRAINSTORMING
Generate {n_thoughts} distinct initial thoughts or approaches to solve this problem.
Do not evaluate them yet. Just list them as clear, actionable starting points.
Format your output strictly as a JSON list of strings, e.g., ["Thought 1...", "Thought 2..."].
"""
        return prompt.strip()

    @staticmethod
    def evaluate_thoughts(problem_statement: str, thoughts: List[str]) -> str:
        """
        Generates a prompt to evaluate the feasibility and promise of each thought.
        """
        thoughts_str = json.dumps(thoughts, indent=2)
        prompt = f"""
PROBLEM: {problem_statement}

Step 2: EVALUATION
I have the following potential approaches (thoughts):
{thoughts_str}

Evaluate each thought critically. Consider:
- Feasibility: Can it be done with available resources?
- Impact: Will it solve the problem effectively?
- Risks: What could go wrong?

For each thought, assign a score from 0.0 (bad) to 1.0 (perfect) and provide a brief reasoning.
Return your evaluation as a JSON list of objects:
[
  {{"thought_index": 0, "score": 0.8, "reasoning": "..."}},
  ...
]
"""
        return prompt.strip()

    @staticmethod
    def expand_thought(problem_statement: str, thought: str, history: str = "") -> str:
        """
        Generates a prompt to expand a specific thought into a concrete plan or solution.
        """
        prompt = f"""
PROBLEM: {problem_statement}

Selected Approach: {thought}
Previous Context: {history}

Step 3: EXPANSION
Develop this thought into a detailed, step-by-step solution.
Address potential challenges mentioned in the evaluation.
Provide the final output in a clear, structured markdown format.
"""
        return prompt.strip()
