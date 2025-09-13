"""
Plan Fix Tool

This MCP tool analyzes the codebase and generates a plan for fixing the issue,
including specific code changes and diffs.
"""

import os
import re
from typing import Dict, Any, List
from openai import AsyncOpenAI

from models.ticket import AnalysisResult, FixPlan, CodeFile, CodeDiff
from utils.logger import logger
from services.github_service import github_service

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def plan_fix_tool(arguments: Dict[str, Any]) -> FixPlan:
  """
  Generate a fix plan based on analysis results and codebase context.
  
  Args:
    arguments: Contains analysis_result and optional repo_path
    
  Returns:
    FixPlan with code changes and implementation steps
  """
  logger.info("Starting fix planning...")
  
  # Parse analysis result
  analysis_data = arguments.get("analysis_result", {})
  repo_path = arguments.get("repo_path", ".")
  
  # Mock analysis result if not provided (for testing)
  if not analysis_data:
    logger.warning("No analysis result provided, using mock data")
    analysis_data = {
      "title": "Mock Bug Fix",
      "code_queries": ["error", "bug"],
      "confidence": 0.5
    }
  
  # Find relevant files based on code queries
  relevant_files = await _search_files(analysis_data.get("code_queries", []), repo_path)
  
  # Analyze each file for potential issues
  file_analysis = await _analyze_files(relevant_files, analysis_data)
  
  # Generate fix plan using AI
  fix_plan = await _generate_fix_plan(analysis_data, file_analysis)
  
  logger.info(f"Fix plan generated with confidence: {fix_plan.confidence}")
  return fix_plan

async def _search_files(code_queries: List[str], repo_path: str) -> List[CodeFile]:
  """
  Find files that might be relevant to the issue.
  
  Args:
    code_queries: Search terms from analysis
    repo_path: Repository root path
    
  Returns:
    List of potentially relevant code files
  """
  logger.info(f"Searching for files matching queries: {code_queries}")
  
  # Common file extensions to search
  extensions = ['.js', '.ts', '.py', '.java', '.go', '.rb', '.php']
  
  # Use GitHub service to search for files
  try:
    files = await github_service.search_files(code_queries, extensions)
    logger.info(f"Found {len(files)} relevant files from GitHub")
    return files
  except Exception as e:
    logger.error(f"GitHub search failed: {str(e)}, using fallback")
    return _get_fallback_files(code_queries)

def _get_fallback_files(code_queries: List[str]) -> List[CodeFile]:
  """Fallback mock files for demo reliability."""
  mock_files = [
    CodeFile(
      path="src/controllers/cart.js",
      reason="Matches 'cart' query and likely contains checkout logic",
      current_content=_get_mock_file_content("cart_controller")
    ),
    CodeFile(
      path="src/services/payment.js", 
      reason="Payment processing often related to checkout issues",
      current_content=_get_mock_file_content("payment_service")
    ),
    CodeFile(
      path="src/models/user.js",
      reason="User model might contain cartId property",
      current_content=_get_mock_file_content("user_model")
    )
  ]
  
  # Filter files based on queries
  relevant_files = []
  for file in mock_files:
    file_text = f"{file.path} {file.reason}".lower()
    if any(query.lower() in file_text for query in code_queries):
      relevant_files.append(file)
  
  return relevant_files

async def _analyze_files(files: List[CodeFile], analysis_data: Dict[str, Any]) -> Dict[str, Any]:
  """
  Analyze files to understand the codebase context.
  
  Args:
    files: List of code files to analyze
    analysis_data: Original analysis results
    
  Returns:
    Dictionary with file analysis results
  """
  logger.info("Analyzing code files...")
  
  file_summaries = []
  potential_issues = []
  
  for file in files:
    # Simple pattern matching for common issues
    content = file.current_content or ""
    
    issues_found = []
    if "cartId" in content and "null" in analysis_data.get("title", "").lower():
      issues_found.append("Potential null cartId usage")
    
    if "async" in content and "await" not in content:
      issues_found.append("Missing await for async operation")
    
    if "req.body" in content and "validation" not in content.lower():
      issues_found.append("Missing input validation")
    
    file_summaries.append({
      "path": file.path,
      "issues": issues_found,
      "lines_of_code": len(content.split('\n')) if content else 0
    })
    
    potential_issues.extend(issues_found)
  
  return {
    "file_summaries": file_summaries,
    "potential_issues": potential_issues,
    "total_files": len(files)
  }

async def _generate_fix_plan(analysis_data: Dict[str, Any], file_analysis: Dict[str, Any]) -> FixPlan:
  """
  Generate the actual fix plan using AI.
  
  Args:
    analysis_data: Original ticket analysis
    file_analysis: Code analysis results
    
  Returns:
    Complete FixPlan with diffs and steps
  """
  logger.info("Generating AI-powered fix plan...")
  
  prompt = f"""
  Generate a fix plan for this issue:
  
  Title: {analysis_data.get('title', 'Unknown issue')}
  Code Issues Found: {file_analysis.get('potential_issues', [])}
  Files Analyzed: {[f['path'] for f in file_analysis.get('file_summaries', [])]}
  
  Provide a JSON response with:
  1. "diffs": Array of code changes with path, patch (git diff format), description
  2. "commit_message": Clear commit message following conventional commits
  3. "checklist": Array of implementation steps
  4. "confidence": Float 0-1 based on issue clarity
  5. "estimated_effort": "Low", "Medium", or "High"
  
  Make changes minimal and focused. Include proper error handling.
  """
  
  try:
    response = await openai_client.chat.completions.create(
      model="gpt-4o-mini",
      messages=[
        {"role": "system", "content": "You are a senior developer creating minimal, safe code fixes. Respond only with valid JSON."},
        {"role": "user", "content": prompt}
      ],
      temperature=0.1,
      max_tokens=1500
    )
    
    import json
    ai_result = json.loads(response.choices[0].message.content)
    
    # Convert AI result to FixPlan model
    diffs = [
      CodeDiff(
        path=diff.get("path", ""),
        patch=diff.get("patch", ""),
        description=diff.get("description", "")
      )
      for diff in ai_result.get("diffs", [])
    ]
    
    return FixPlan(
      files=[],  # Files already analyzed above
      diffs=diffs,
      commit_message=ai_result.get("commit_message", "fix: resolve issue"),
      checklist=ai_result.get("checklist", ["Apply code changes", "Test functionality"]),
      confidence=ai_result.get("confidence", 0.5),
      estimated_effort=ai_result.get("estimated_effort", "Medium")
    )
    
  except Exception as e:
    logger.warning(f"AI fix generation failed: {str(e)}, using fallback")
    
    # Fallback fix plan
    return FixPlan(
      files=[],
      diffs=[
        CodeDiff(
          path="src/controllers/cart.js",
          patch=_generate_fallback_patch(),
          description="Add null check for cartId parameter"
        )
      ],
      commit_message="fix: add null check for cartId in cart controller",
      checklist=[
        "Add null/undefined validation for cartId",
        "Return appropriate error response",
        "Add unit test for null cartId case",
        "Test in staging environment"
      ],
      confidence=0.4,
      estimated_effort="Low"
    )

def _get_mock_file_content(file_type: str) -> str:
  """Generate mock file content for demo purposes."""
  
  mock_contents = {
    "cart_controller": """
const express = require('express');
const CartService = require('../services/cart');

const router = express.Router();

router.post('/cart', async (req, res) => {
  try {
    const { cartId, items } = req.body;
    const result = await CartService.updateCart(cartId, items);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
""",
    "payment_service": """
class PaymentService {
  static async processPayment(cartId, paymentData) {
    if (!cartId) {
      throw new Error('Cart ID is required');
    }
    
    // Payment processing logic
    return { success: true, transactionId: 'tx_123' };
  }
}

module.exports = PaymentService;
""",
    "user_model": """
const mongoose = require('mongoose');

const userSchema = new mongoose.Schema({
  email: String,
  cartId: { type: String, default: null },
  createdAt: { type: Date, default: Date.now }
});

module.exports = mongoose.model('User', userSchema);
"""
  }
  
  return mock_contents.get(file_type, "// Mock file content")

def _generate_fallback_patch() -> str:
  """Generate a simple fallback patch for demo."""
  return """--- a/src/controllers/cart.js
+++ b/src/controllers/cart.js
@@ -5,6 +5,10 @@
 router.post('/cart', async (req, res) => {
   try {
     const { cartId, items } = req.body;
+    if (!cartId) {
+      return res.status(400).json({ error: 'cartId is required' });
+    }
+    
     const result = await CartService.updateCart(cartId, items);
     res.json(result);
   } catch (error) {"""
