"""
Log Handlers for TechSaaS

This module provides custom logging handlers for different output destinations,
including database storage and specialized file handlers with compression.
"""

import os
import gzip
import time
import logging
import sqlite3
import threading
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, Optional, List, Union

from api.v1.utils.logging.core import get_logger


logger = get_logger("techsaas.handlers")


class RotatingFileHandlerWithCompression(RotatingFileHandler):
    """
    A rotating file handler that compresses rotated log files.
    
    This handler extends the standard RotatingFileHandler to automatically
    compress log files after rotation, reducing disk usage while maintaining
    log history.
    """
    
    def __init__(
        self,
        filename: str,
        mode: str = 'a',
        maxBytes: int = 0,
        backupCount: int = 0,
        encoding: Optional[str] = None,
        delay: bool = False,
        compress_rotated: bool = True,
    ):
        """
        Initialize the handler.
        
        Args:
            filename: Log file name
            mode: File open mode
            maxBytes: Maximum size in bytes before rotation
            backupCount: Number of backup files to keep
            encoding: File encoding
            delay: Delay file creation until first log
            compress_rotated: Whether to compress rotated files
        """
        super().__init__(
            filename, mode, maxBytes, backupCount, encoding, delay
        )
        self.compress_rotated = compress_rotated
        self._rotateLock = threading.RLock()
    
    def doRollover(self) -> None:
        """
        Perform log rotation with compression of rotated files.
        """
        if self.stream:
            self.stream.close()
            self.stream = None
        
        with self._rotateLock:
            # Rotate the files
            if self.backupCount > 0:
                # Remove the oldest log file if it exists
                oldest_backup = f"{self.baseFilename}.{self.backupCount}.gz"
                if os.path.exists(oldest_backup):
                    try:
                        os.remove(oldest_backup)
                    except OSError as e:
                        logger.error(f"Error removing old log file {oldest_backup}: {e}")
                
                # Shift compressed backups
                for i in range(self.backupCount - 1, 0, -1):
                    sfn = f"{self.baseFilename}.{i}.gz"
                    dfn = f"{self.baseFilename}.{i + 1}.gz"
                    if os.path.exists(sfn):
                        try:
                            os.rename(sfn, dfn)
                        except OSError as e:
                            logger.error(f"Error renaming {sfn} to {dfn}: {e}")
                
                # Rename the current log file
                dfn = f"{self.baseFilename}.1"
                if os.path.exists(self.baseFilename):
                    try:
                        os.rename(self.baseFilename, dfn)
                        # Compress the rotated file
                        if self.compress_rotated:
                            with open(dfn, 'rb') as f_in:
                                with gzip.open(f"{dfn}.gz", 'wb') as f_out:
                                    f_out.writelines(f_in)
                            # Remove the uncompressed file
                            os.remove(dfn)
                    except OSError as e:
                        logger.error(f"Error rotating log file {self.baseFilename}: {e}")
            
            # Open new log file
            self.mode = 'w'
            self.stream = self._open()


class DatabaseLogHandler(logging.Handler):
    """
    A handler that writes log records to a SQLite database.
    
    This handler stores logs in a structured database format for easy querying
    and analysis, making it ideal for admin dashboards and monitoring tools.
    """
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        table_name: str = 'application_logs',
        level: int = logging.NOTSET,
        batch_size: int = 100,
        flush_interval: int = 60,  # Seconds
    ):
        """
        Initialize the database log handler.
        
        Args:
            db_path: Path to SQLite database file
            table_name: Name of the table to store logs
            level: Minimum logging level
            batch_size: Number of records to batch before committing
            flush_interval: Time interval in seconds to flush pending records
        """
        super().__init__(level)
        
        # Set database path
        if db_path is None:
            # Default to logs directory
            log_dir = os.path.join(os.getcwd(), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            db_path = os.path.join(log_dir, 'logs.db')
        
        self.db_path = db_path
        self.table_name = table_name
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # Batching and threading
        self.buffer = []
        self.buffer_lock = threading.RLock()
        self.last_flush = time.time()
        self.flush_timer = None
        
        # Initialize database
        self._init_db()
        
        # Start flush timer
        self._start_flush_timer()
    
    def _init_db(self) -> None:
        """Initialize the database and create tables if they don't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create logs table
            cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                logger TEXT NOT NULL,
                module TEXT NOT NULL,
                message TEXT NOT NULL,
                request_id TEXT,
                user_id TEXT,
                ip_address TEXT,
                method TEXT,
                path TEXT,
                status_code INTEGER,
                response_time REAL,
                exception TEXT,
                stack_trace TEXT,
                extra_data TEXT
            )
            ''')
            
            # Create index for faster queries
            cursor.execute(f'''
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_timestamp 
            ON {self.table_name} (timestamp)
            ''')
            
            cursor.execute(f'''
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_level 
            ON {self.table_name} (level)
            ''')
            
            cursor.execute(f'''
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_user_id 
            ON {self.table_name} (user_id)
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def _start_flush_timer(self) -> None:
        """Start a timer to periodically flush records to the database."""
        def flush_timer():
            self.flush()
            self.flush_timer = threading.Timer(self.flush_interval, flush_timer)
            self.flush_timer.daemon = True
            self.flush_timer.start()
        
        self.flush_timer = threading.Timer(self.flush_interval, flush_timer)
        self.flush_timer.daemon = True
        self.flush_timer.start()
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Add a log record to the buffer.
        
        Args:
            record: LogRecord to store
        """
        try:
            # Format the record
            log_entry = self._format_record(record)
            
            # Add to buffer
            with self.buffer_lock:
                self.buffer.append(log_entry)
                
                # Flush if buffer exceeds batch size
                if len(self.buffer) >= self.batch_size:
                    self.flush()
                
        except Exception as e:
            logger.error(f"Error emitting log record: {e}")
    
    def _format_record(self, record: logging.LogRecord) -> Dict[str, Any]:
        """
        Format a log record for database storage.
        
        Args:
            record: LogRecord to format
            
        Returns:
            Dictionary of values to store in the database
        """
        # Basic record info
        log_entry = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created)),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'message': record.getMessage(),
            'request_id': getattr(record, 'request_id', None),
            'user_id': getattr(record, 'user_id', None),
            'ip_address': getattr(record, 'ip', None),
            'method': getattr(record, 'method', None),
            'path': getattr(record, 'path', None),
            'status_code': getattr(record, 'status', None),
            'response_time': getattr(record, 'response_time', None),
            'exception': None,
            'stack_trace': None,
            'extra_data': None
        }
        
        # Exception info
        if record.exc_info:
            import traceback
            log_entry['exception'] = str(record.exc_info[1])
            log_entry['stack_trace'] = '\n'.join(traceback.format_exception(*record.exc_info))
        
        # Extra data
        extra_data = {}
        for key, value in record.__dict__.items():
            if key not in ['timestamp', 'level', 'logger', 'module', 'message', 
                          'request_id', 'user_id', 'ip_address', 'method', 'path', 
                          'status_code', 'response_time', 'exception', 'stack_trace'] and \
               not key.startswith('_') and \
               not callable(value):
                extra_data[key] = str(value)
        
        if extra_data:
            import json
            log_entry['extra_data'] = json.dumps(extra_data)
        
        return log_entry
    
    def flush(self) -> None:
        """Flush buffered records to the database."""
        with self.buffer_lock:
            if not self.buffer:
                return
            
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Prepare SQL
                placeholders = ', '.join(['?'] * 16)
                sql = f'''
                INSERT INTO {self.table_name} (
                    timestamp, level, logger, module, message, 
                    request_id, user_id, ip_address, method, path, 
                    status_code, response_time, exception, stack_trace, 
                    extra_data, id
                ) VALUES ({placeholders})
                '''
                
                # Prepare data
                values = []
                for entry in self.buffer:
                    values.append((
                        entry['timestamp'],
                        entry['level'],
                        entry['logger'],
                        entry['module'],
                        entry['message'],
                        entry['request_id'],
                        entry['user_id'],
                        entry['ip_address'],
                        entry['method'],
                        entry['path'],
                        entry['status_code'],
                        entry['response_time'],
                        entry['exception'],
                        entry['stack_trace'],
                        entry['extra_data'],
                        None  # ID is auto-incremented
                    ))
                
                # Execute and commit
                cursor.executemany(sql, values)
                conn.commit()
                conn.close()
                
                # Clear buffer
                self.buffer = []
                self.last_flush = time.time()
                
            except Exception as e:
                logger.error(f"Error flushing logs to database: {e}")
    
    def close(self) -> None:
        """Close the handler and flush any remaining records."""
        try:
            # Cancel timer
            if self.flush_timer:
                self.flush_timer.cancel()
            
            # Flush remaining records
            self.flush()
            
        finally:
            super().close()
