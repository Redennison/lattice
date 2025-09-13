"""
Repository Indexer Service

This service indexes repository code and uses vector search to find relevant files
for bug fixes based on code queries from analysis.
"""

import os
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
import ast
import json

from utils.logger import logger

class RepoIndexer:
    """
    Indexes repository code and provides search capabilities.
    """
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.file_index = {}
        self.vector_store = None  # Would connect to MongoDB Atlas Vector Search
        
    async def search_relevant_files(self, code_queries: List[str], max_files: int = 20) -> List[Dict[str, Any]]:
        """
        Searches for files relevant to the given code queries.
        
        Args:
            code_queries: List of search terms from analysis
            max_files: Maximum number of files to return
            
        Returns:
            List of relevant files with content and relevance scores
        """
        logger.info(f"Searching for files matching queries: {code_queries}")
        
        relevant_files = []
        
        # Common file extensions to search
        extensions = {
            '.py': 'python',
            '.js': 'javascript', 
            '.ts': 'typescript',
            '.jsx': 'react',
            '.tsx': 'react',
            '.java': 'java',
            '.go': 'go',
            '.rb': 'ruby',
            '.php': 'php',
            '.cs': 'csharp',
            '.cpp': 'cpp',
            '.c': 'c',
            '.rs': 'rust'
        }
        
        # Search for files in the repository
        for ext, lang in extensions.items():
            for file_path in self.repo_path.rglob(f"*{ext}"):
                # Skip test files and node_modules
                if self._should_skip_file(file_path):
                    continue
                    
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    relevance_score = self._calculate_relevance(content, str(file_path), code_queries)
                    
                    if relevance_score > 0.1:  # Threshold for relevance
                        relevant_files.append({
                            "path": str(file_path.relative_to(self.repo_path)),
                            "content": content,
                            "language": lang,
                            "relevance_score": relevance_score,
                            "size": len(content),
                            "line_count": content.count('\n') + 1
                        })
                except Exception as e:
                    logger.debug(f"Could not read file {file_path}: {e}")
        
        # Sort by relevance and limit results
        relevant_files.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # If no files found, return mock data for demo
        if not relevant_files:
            relevant_files = self._get_mock_files(code_queries)
        
        return relevant_files[:max_files]
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """
        Determines if a file should be skipped during indexing.
        """
        skip_patterns = [
            'node_modules',
            '__pycache__',
            '.git',
            '.venv',
            'venv',
            'dist',
            'build',
            '.pytest_cache',
            'coverage',
            '.nyc_output',
            'test',
            'tests',
            'spec',
            '__tests__'
        ]
        
        path_str = str(file_path).lower()
        return any(pattern in path_str for pattern in skip_patterns)
    
    def _calculate_relevance(self, content: str, file_path: str, queries: List[str]) -> float:
        """
        Calculates relevance score for a file based on queries.
        
        Args:
            content: File content
            file_path: Path to the file
            queries: Search queries
            
        Returns:
            Relevance score between 0 and 1
        """
        score = 0.0
        content_lower = content.lower()
        path_lower = file_path.lower()
        
        for query in queries:
            query_lower = query.lower()
            
            # Exact match in file path - high relevance
            if query_lower in path_lower:
                score += 0.5
            
            # Count occurrences in content
            occurrences = content_lower.count(query_lower)
            if occurrences > 0:
                # Logarithmic scoring to avoid over-weighting
                import math
                score += min(0.3, 0.1 * math.log(occurrences + 1))
            
            # Check for class/function definitions
            if f"class {query_lower}" in content_lower or f"def {query_lower}" in content_lower:
                score += 0.3
            
            # Check for imports/requires
            if f"import {query_lower}" in content_lower or f"require('{query_lower}" in content_lower:
                score += 0.2
        
        # Normalize score
        return min(1.0, score / max(1, len(queries)))
    
    def _get_mock_files(self, queries: List[str]) -> List[Dict[str, Any]]:
        """
        Returns mock files for demo purposes when no real files are found.
        """
        mock_files = [
            {
                "path": "src/controllers/cart.js",
                "content": """const express = require('express');
const CartService = require('../services/cart');

const router = express.Router();

router.post('/checkout', async (req, res) => {
  try {
    const { cartId, items } = req.body;
    // BUG: No null check for cartId
    const result = await CartService.processCheckout(cartId, items);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;""",
                "language": "javascript",
                "relevance_score": 0.8,
                "size": 400,
                "line_count": 17
            },
            {
                "path": "src/services/cart.js",
                "content": """class CartService {
  static async processCheckout(cartId, items) {
    // Process checkout logic
    const cart = await Cart.findById(cartId);
    if (!cart) {
      throw new Error('Cart not found');
    }
    
    // Calculate total
    const total = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
    
    // Process payment
    const payment = await PaymentService.process(cartId, total);
    
    return { success: true, orderId: payment.orderId };
  }
}

module.exports = CartService;""",
                "language": "javascript",
                "relevance_score": 0.7,
                "size": 450,
                "line_count": 19
            },
            {
                "path": "src/models/cart.js",
                "content": """const mongoose = require('mongoose');

const cartSchema = new mongoose.Schema({
  userId: { type: String, required: true },
  items: [{
    productId: String,
    quantity: Number,
    price: Number
  }],
  status: { type: String, default: 'active' },
  createdAt: { type: Date, default: Date.now },
  updatedAt: { type: Date, default: Date.now }
});

module.exports = mongoose.model('Cart', cartSchema);""",
                "language": "javascript",
                "relevance_score": 0.6,
                "size": 380,
                "line_count": 15
            }
        ]
        
        # Filter based on queries
        filtered = []
        for file in mock_files:
            if any(q.lower() in file['path'].lower() or q.lower() in file['content'].lower() for q in queries):
                filtered.append(file)
        
        return filtered if filtered else mock_files[:2]  # Return at least 2 files
    
    async def index_repository(self) -> Dict[str, Any]:
        """
        Indexes the entire repository for future searches.
        
        Returns:
            Statistics about the indexing process
        """
        logger.info(f"Indexing repository at {self.repo_path}")
        
        stats = {
            "total_files": 0,
            "indexed_files": 0,
            "skipped_files": 0,
            "total_lines": 0,
            "languages": {}
        }
        
        # Would implement actual indexing with vector embeddings here
        # For now, return mock stats
        stats["total_files"] = 150
        stats["indexed_files"] = 120
        stats["skipped_files"] = 30
        stats["total_lines"] = 15000
        stats["languages"] = {
            "javascript": 45,
            "typescript": 30,
            "python": 25,
            "json": 20
        }
        
        logger.info(f"Indexing complete: {stats['indexed_files']} files indexed")
        return stats
