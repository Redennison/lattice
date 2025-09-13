import logging
import sys
from pathlib import Path
from typing import Optional
import os

def setup_logger(
  name: str = "mcp_server",
  level: Optional[str] = None,
  log_file: Optional[str] = None
) -> logging.Logger:
  """
  Set up structured logging for the MCP server.
  
  Args:
    name: Logger name
    level: Log level (DEBUG, INFO, WARNING, ERROR)
    log_file: Optional log file path
  
  Returns:
    Configured logger instance
  """

  # Get log level from environment or use provided level
  log_level = level or os.getenv("LOG_LEVEL", "INFO")
  log_file_path = log_file or os.getenv("LOG_FILE")
    
  # Create logger
  logger = logging.getLogger(name)
  logger.setLevel(getattr(logging, log_level.upper()))
    
  # Clear existing handlers
  logger.handlers.clear()
    
  # Create formatter
  formatter = logging.Formatter(
    fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
  )
    
  # Console handler
  console_handler = logging.StreamHandler(sys.stdout)
  console_handler.setFormatter(formatter)
  logger.addHandler(console_handler)
    
  # File handler (if specified)
  if log_file_path:
    log_path = Path(log_file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
        
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
  return logger

# Global logger instance
logger = setup_logger()
