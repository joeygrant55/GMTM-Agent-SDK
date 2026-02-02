"""
GMTM Database Connector
=======================

Direct MySQL connection to GMTM database.
Bypasses MCP to avoid iCloud sync issues.
"""

import os
import mysql.connector
from mysql.connector import Error
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class GMTMDatabase:
    """Direct connection to GMTM MySQL database"""
    
    def __init__(self):
        self.config = {
            'host': os.getenv('DB_HOST'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_NAME'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'raise_on_warnings': True
        }
        self.connection = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = mysql.connector.connect(**self.config)
            if self.connection.is_connected():
                db_info = self.connection.get_server_info()
                print(f"✅ Connected to GMTM MySQL Server version {db_info}")
                return True
        except Error as e:
            print(f"❌ Error connecting to MySQL: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("✅ MySQL connection closed")
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results as list of dicts.
        
        Args:
            query: SQL query string
            params: Optional tuple of parameters for prepared statement
            
        Returns:
            List of dictionaries (one per row)
        """
        if not self.connection or not self.connection.is_connected():
            if not self.connect():
                raise Exception("Failed to connect to database")
        
        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            results = cursor.fetchall()
            return results
        except Error as e:
            print(f"❌ Query error: {e}")
            print(f"Query: {query[:200]}...")
            raise
        finally:
            if cursor:
                cursor.close()
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column information for a table"""
        query = f"DESCRIBE {table_name}"
        return self.execute_query(query)
    
    def test_connection(self) -> Dict[str, Any]:
        """Test database connection and return basic stats"""
        if not self.connect():
            return {"status": "error", "message": "Connection failed"}
        
        try:
            # Get database info
            cursor = self.connection.cursor()
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            
            # Get athlete count
            cursor.execute("SELECT COUNT(*) FROM users WHERE type = 1")
            athlete_count = cursor.fetchone()[0]
            
            # Get metrics count
            cursor.execute("SELECT COUNT(*) FROM metrics WHERE verified = 1")
            metrics_count = cursor.fetchone()[0]
            
            cursor.close()
            
            return {
                "status": "success",
                "database": db_name,
                "athlete_count": athlete_count,
                "verified_metrics_count": metrics_count,
                "host": self.config['host']
            }
        except Error as e:
            return {"status": "error", "message": str(e)}
        finally:
            self.disconnect()

# Global database instance
_db_instance = None

def get_db() -> GMTMDatabase:
    """Get or create global database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = GMTMDatabase()
    return _db_instance

def run_sql(query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    """
    Convenience function to run SQL query.
    Automatically manages connection.
    """
    db = get_db()
    return db.execute_query(query, params)
