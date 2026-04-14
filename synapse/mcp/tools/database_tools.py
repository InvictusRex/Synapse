"""
Database Tools - SQLite operations
Create, query, and manage local SQLite databases
"""
import os
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime


def create_database(db_path: str) -> Dict[str, Any]:
    """Create a new SQLite database file"""
    try:
        db_path = os.path.expanduser(db_path)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        
        # Create the database (just connecting creates it if it doesn't exist)
        conn = sqlite3.connect(db_path)
        conn.close()
        
        return {
            "success": True,
            "database": os.path.abspath(db_path),
            "message": "Database created successfully"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_sql(db_path: str, sql: str, params: List = None) -> Dict[str, Any]:
    """
    Execute a SQL statement
    
    Args:
        db_path: Path to SQLite database
        sql: SQL statement to execute
        params: Optional parameters for parameterized queries
    """
    try:
        db_path = os.path.expanduser(db_path)
        
        if not os.path.exists(db_path):
            return {"success": False, "error": f"Database not found: {db_path}"}
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        
        # Check if this is a SELECT query
        if sql.strip().upper().startswith("SELECT"):
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            results = [dict(row) for row in rows]
            
            conn.close()
            return {
                "success": True,
                "columns": columns,
                "rows": results,
                "row_count": len(results)
            }
        else:
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            
            return {
                "success": True,
                "affected_rows": affected,
                "message": "Query executed successfully"
            }
            
    except sqlite3.Error as e:
        return {"success": False, "error": f"SQL Error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_table(db_path: str, table_name: str, columns: Dict[str, str]) -> Dict[str, Any]:
    """
    Create a table in the database
    
    Args:
        db_path: Path to SQLite database
        table_name: Name of the table to create
        columns: Dict of column_name -> column_type (e.g., {"id": "INTEGER PRIMARY KEY", "name": "TEXT"})
    """
    try:
        column_defs = ", ".join([f"{name} {dtype}" for name, dtype in columns.items()])
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({column_defs})"
        
        result = execute_sql(db_path, sql)
        
        if result["success"]:
            return {
                "success": True,
                "table": table_name,
                "columns": list(columns.keys()),
                "message": f"Table '{table_name}' created successfully"
            }
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def insert_data(db_path: str, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert a row into a table
    
    Args:
        db_path: Path to SQLite database
        table_name: Name of the table
        data: Dict of column_name -> value
    """
    try:
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        
        return execute_sql(db_path, sql, list(data.values()))
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def query_table(db_path: str, table_name: str, where: str = None, limit: int = 100) -> Dict[str, Any]:
    """
    Query data from a table
    
    Args:
        db_path: Path to SQLite database
        table_name: Name of the table
        where: Optional WHERE clause (without 'WHERE' keyword)
        limit: Maximum rows to return (default 100)
    """
    try:
        sql = f"SELECT * FROM {table_name}"
        if where:
            sql += f" WHERE {where}"
        sql += f" LIMIT {limit}"
        
        return execute_sql(db_path, sql)
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_tables(db_path: str) -> Dict[str, Any]:
    """List all tables in a database"""
    try:
        sql = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        result = execute_sql(db_path, sql)
        
        if result["success"]:
            tables = [row["name"] for row in result["rows"]]
            return {
                "success": True,
                "database": db_path,
                "tables": tables,
                "count": len(tables)
            }
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def describe_table(db_path: str, table_name: str) -> Dict[str, Any]:
    """Get schema information for a table"""
    try:
        sql = f"PRAGMA table_info({table_name})"
        result = execute_sql(db_path, sql)
        
        if result["success"]:
            columns = []
            for row in result["rows"]:
                columns.append({
                    "name": row["name"],
                    "type": row["type"],
                    "nullable": not row["notnull"],
                    "primary_key": bool(row["pk"]),
                    "default": row["dflt_value"]
                })
            
            return {
                "success": True,
                "table": table_name,
                "columns": columns
            }
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_data(db_path: str, table_name: str, where: str) -> Dict[str, Any]:
    """
    Delete rows from a table
    
    Args:
        db_path: Path to SQLite database
        table_name: Name of the table
        where: WHERE clause (required for safety)
    """
    try:
        if not where:
            return {"success": False, "error": "WHERE clause is required for DELETE operations"}
        
        sql = f"DELETE FROM {table_name} WHERE {where}"
        return execute_sql(db_path, sql)
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def update_data(db_path: str, table_name: str, data: Dict[str, Any], where: str) -> Dict[str, Any]:
    """
    Update rows in a table
    
    Args:
        db_path: Path to SQLite database
        table_name: Name of the table
        data: Dict of column_name -> new_value
        where: WHERE clause (required for safety)
    """
    try:
        if not where:
            return {"success": False, "error": "WHERE clause is required for UPDATE operations"}
        
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        sql = f"UPDATE {table_name} SET {set_clause} WHERE {where}"
        
        return execute_sql(db_path, sql, list(data.values()))
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def export_to_csv(db_path: str, table_name: str, output_path: str) -> Dict[str, Any]:
    """Export a table to CSV file"""
    try:
        import csv
        
        result = query_table(db_path, table_name, limit=10000)
        
        if not result["success"]:
            return result
        
        output_path = os.path.expanduser(output_path)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            if result["rows"]:
                writer = csv.DictWriter(f, fieldnames=result["columns"])
                writer.writeheader()
                writer.writerows(result["rows"])
        
        return {
            "success": True,
            "exported_to": os.path.abspath(output_path),
            "rows_exported": result["row_count"]
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
