"""
Database utilities with retry logic and connection management
"""
import time
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, OperationalError
from utils.logger import database_logger

def retry_db_operation(max_retries=3, delay=1, backoff=2):
    """
    Decorator để retry database operations với exponential backoff
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                    
                except (DisconnectionError, OperationalError) as e:
                    last_exception = e
                    if attempt == max_retries - 1:
                        database_logger.error(
                            f"Database connection failed after {max_retries} attempts",
                            error_type='ConnectionError',
                            max_retries=max_retries,
                            error_details=str(e)
                        )
                        raise
                    
                    wait_time = delay * (backoff ** attempt)
                    database_logger.warning(
                        f"Database connection error, retrying in {wait_time}s",
                        error_type='ConnectionRetry',
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        wait_time=wait_time,
                        error_details=str(e)
                    )
                    time.sleep(wait_time)
                    
                except SQLAlchemyError as e:
                    database_logger.error(
                        f"Database operation failed",
                        error_type='SQLAlchemyError',
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        error_details=str(e)
                    )
                    raise
                    
                except Exception as e:
                    database_logger.error(
                        f"Unexpected error in database operation",
                        error_type='UnexpectedError',
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        error_details=str(e)
                    )
                    raise
                    
            raise last_exception
        return wrapper
    return decorator

def safe_db_commit(db_session, operation_name="database operation"):
    """
    Safely commit database transaction với error handling
    """
    try:
        db_session.commit()
        database_logger.info(f"Successfully committed {operation_name}")
        return True
        
    except SQLAlchemyError as e:
        database_logger.error(
            f"Failed to commit {operation_name}",
            error_type='CommitError',
            error_details=str(e)
        )
        db_session.rollback()
        return False
        
    except Exception as e:
        database_logger.critical(
            f"Unexpected error during {operation_name}",
            error_type='UnexpectedCommitError',
            error_details=str(e)
        )
        db_session.rollback()
        return False

def safe_db_rollback(db_session, operation_name="database operation"):
    """
    Safely rollback database transaction
    """
    try:
        db_session.rollback()
        database_logger.info(f"Successfully rolled back {operation_name}")
        
    except Exception as e:
        database_logger.error(
            f"Failed to rollback {operation_name}",
            error_type='RollbackError',
            error_details=str(e)
        )

class DatabaseHealthCheck:
    """Database health check utility"""
    
    def __init__(self, db_session):
        self.db_session = db_session
    
    def check_connection(self):
        """Kiểm tra kết nối database"""
        try:
            # Thực hiện query đơn giản để test connection
            self.db_session.execute("SELECT 1")
            database_logger.info("Database connection health check passed")
            return True
            
        except Exception as e:
            database_logger.error(
                "Database connection health check failed",
                error_type='HealthCheckError',
                error_details=str(e)
            )
            return False
    
    def check_table_exists(self, table_name):
        """Kiểm tra table có tồn tại không"""
        try:
            result = self.db_session.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
            )
            exists = result.fetchone() is not None
            database_logger.info(f"Table {table_name} exists check: {exists}")
            return exists
            
        except Exception as e:
            database_logger.error(
                f"Failed to check if table {table_name} exists",
                error_type='TableCheckError',
                table_name=table_name,
                error_details=str(e)
            )
            return False
