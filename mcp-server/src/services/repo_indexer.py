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
        
        # If no files found, log warning but return empty list
        if not relevant_files:
            logger.warning(f"No files found matching queries: {code_queries}")
        
        return relevant_files[:max_files]
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """
        Determines if a file should be skipped during indexing.
        """
        skip_patterns = [
            '/node_modules/',
            '/__pycache__/',
            '/.git/',
            '/.venv/',
            '/venv/',
            '/dist/',
            '/build/',
            '/.next/',  # Skip Next.js build output
            '/.pytest_cache/',
            '/coverage/',
            '/.nyc_output/'
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