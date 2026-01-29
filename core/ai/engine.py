import logging
import json
import asyncio
from typing import List, Dict, Optional
from core.ai.prompts import TreeOfThoughtPrompt

# Placeholder for actual LLM client (e.g., OpenAI, Gemini, etc.)
# In a real integration, we would import the specific client here.
# For now, we'll mock the LLM call or assume a `call_llm` function exists in core.utils
# or we can just log what would happen.

logger = logging.getLogger("SmartAgent")

class SmartAgent:
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.model_name = model_name
        self.prompt_engine = TreeOfThoughtPrompt()
        
        # Initialize Gemini
        import os
        import google.generativeai as genai
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
        else:
            self.model = None
            logger.warning("GOOGLE_API_KEY missing for SmartAgent.")
    
    async def _call_llm(self, prompt: str) -> str:
        """
        Calls Gemini 1.5 Flash API.
        """
        if not self.model:
             logger.warning("SmartAgent not configured, returning mock.")
             return "AI Not Configured"

        logger.info(f"Thinking... (Model: {self.model_name})")
        
        try:
             # Run sync call in thread
             response = await asyncio.to_thread(self.model.generate_content, prompt)
             return response.text
        except Exception as e:
             logger.error(f"Gemini Error: {e}")
             return f"Error: {str(e)}"

    async def solve(self, problem: str) -> str:
        """
        Solves a complex problem using the Tree of Thoughts method.
        """
        logger.info(f"🧠 SmartAgent analyzing: {problem}")

        # 1. Generate Thoughts
        p1 = self.prompt_engine.generate_thoughts(problem)
        resp1 = await self._call_llm(p1)
        try:
            thoughts = json.loads(resp1)
        except:
            logger.warning("Failed to parse thoughts JSON. Falling back to raw response.")
            return resp1

        logger.info(f"Generated {len(thoughts)} thoughts.")

        # 2. Evaluate Thoughts
        p2 = self.prompt_engine.evaluate_thoughts(problem, thoughts)
        resp2 = await self._call_llm(p2)
        try:
            evaluations = json.loads(resp2)
            # Find best thought
            best_thought_data = max(evaluations, key=lambda x: x['score'])
            best_idx = best_thought_data['thought_index']
            best_thought = thoughts[best_idx]
            logger.info(f"Winning Strategy (Score: {best_thought_data['score']}): {best_thought}")
        except:
            logger.warning("Failed to parse evaluation JSON. Picking first thought.")
            best_thought = thoughts[0]

        # 3. Expand/Execute Best Thought
        p3 = self.prompt_engine.expand_thought(problem, best_thought)
        final_solution = await self._call_llm(p3)
        
        return final_solution
