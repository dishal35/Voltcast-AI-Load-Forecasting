"""
Storage service for historical data and database operations.
Handles retrieval of historical actuals for feature computation.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)


class StorageService:
    """Manages database connections and historical data retrieval."""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize storage service.
        
        Args:
            database_url: Database connection string. If None, uses DATABASE_URL env var.
                         Falls back to SQLite if not provided.
        """
        self.database_url = database_url or os.getenv(
            'DATABASE_URL', 
            'sqlite:///./demand_forecast.db'
        )
        
        # Create engine with appropriate settings
        if self.database_url.startswith('sqlite'):
            self.engine = create_engine(
                self.database_url,
                connect_args={"check_same_thread": False}
            )
        else:
            self.engine = create_engine(
                self.database_url,
                poolclass=NullPool  # Simple for now, can optimize later
            )
        
        logger.info(f"Storage service initialized with {self.database_url.split(':')[0]} database")
    
    def get_last_n_hours(
        self, 
        n: int, 
        until_ts: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Retrieve the last N hours of historical data.
        
        Args:
            n: Number of hours to retrieve
            until_ts: End timestamp (exclusive). If None, uses current time.
        
        Returns:
            DataFrame with columns: ts, demand, temperature, humidity, wind_speed,
                                   solar_generation, cloud_cover, is_holiday
            Sorted by ts ascending (oldest first)
        
        Raises:
            ValueError: If insufficient data available
        """
        if until_ts is None:
            until_ts = datetime.utcnow()
        
        query = text("""
            SELECT ts, demand, temperature, humidity, wind_speed, 
                   solar_generation, cloud_cover, is_holiday
            FROM hourly_actuals
            WHERE ts < :until_ts
            ORDER BY ts DESC
            LIMIT :n
        """)
        
        # Convert pandas Timestamp to Python datetime if needed
        if hasattr(until_ts, 'to_pydatetime'):
            until_ts = until_ts.to_pydatetime()
        
        with self.engine.connect() as conn:
            df = pd.read_sql(query, conn, params={'until_ts': until_ts, 'n': n})
        
        if len(df) == 0:
            raise ValueError(f"No historical data found before {until_ts}")
        
        if len(df) < n:
            logger.warning(
                f"Requested {n} hours but only {len(df)} available before {until_ts}"
            )
        
        # Sort ascending (oldest first) for sequence building
        df = df.sort_values('ts').reset_index(drop=True)
        
        # Ensure datetime type
        df['ts'] = pd.to_datetime(df['ts'])
        
        return df
    
    def get_range(
        self, 
        start_ts: datetime, 
        end_ts: datetime
    ) -> pd.DataFrame:
        """
        Retrieve historical data for a specific time range.
        
        Args:
            start_ts: Start timestamp (inclusive)
            end_ts: End timestamp (exclusive)
        
        Returns:
            DataFrame sorted by ts ascending
        """
        query = text("""
            SELECT ts, demand, temperature, humidity, wind_speed,
                   solar_generation, cloud_cover, is_holiday
            FROM hourly_actuals
            WHERE ts >= :start_ts AND ts < :end_ts
            ORDER BY ts ASC
        """)
        
        # Convert pandas Timestamp to Python datetime if needed
        if hasattr(start_ts, 'to_pydatetime'):
            start_ts = start_ts.to_pydatetime()
        if hasattr(end_ts, 'to_pydatetime'):
            end_ts = end_ts.to_pydatetime()
        
        with self.engine.connect() as conn:
            df = pd.read_sql(
                query, 
                conn, 
                params={'start_ts': start_ts, 'end_ts': end_ts}
            )
        
        df['ts'] = pd.to_datetime(df['ts'])
        return df
    
    def append_actuals(self, df: pd.DataFrame) -> int:
        """
        Append new actual observations to the database.
        
        Args:
            df: DataFrame with columns matching hourly_actuals schema
        
        Returns:
            Number of rows inserted
        """
        required_cols = ['ts', 'demand']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"DataFrame must contain columns: {required_cols}")
        
        # Ensure ts is datetime
        df = df.copy()
        df['ts'] = pd.to_datetime(df['ts'])
        
        # Fill missing columns with None
        for col in ['temperature', 'humidity', 'wind_speed', 
                    'solar_generation', 'cloud_cover', 'is_holiday']:
            if col not in df.columns:
                df[col] = None
        
        # Insert with conflict handling (upsert)
        rows_inserted = 0
        with self.engine.begin() as conn:
            for _, row in df.iterrows():
                # Convert pandas Timestamp to Python datetime for SQLite compatibility
                row_dict = row.to_dict()
                if hasattr(row_dict['ts'], 'to_pydatetime'):
                    row_dict['ts'] = row_dict['ts'].to_pydatetime()
                
                if self.database_url.startswith('sqlite'):
                    query = text("""
                        INSERT OR REPLACE INTO hourly_actuals 
                        (ts, demand, temperature, humidity, wind_speed, 
                         solar_generation, cloud_cover, is_holiday)
                        VALUES (:ts, :demand, :temperature, :humidity, :wind_speed,
                                :solar_generation, :cloud_cover, :is_holiday)
                    """)
                else:
                    query = text("""
                        INSERT INTO hourly_actuals 
                        (ts, demand, temperature, humidity, wind_speed,
                         solar_generation, cloud_cover, is_holiday)
                        VALUES (:ts, :demand, :temperature, :humidity, :wind_speed,
                                :solar_generation, :cloud_cover, :is_holiday)
                        ON CONFLICT (ts) DO UPDATE SET
                            demand = EXCLUDED.demand,
                            temperature = EXCLUDED.temperature,
                            humidity = EXCLUDED.humidity,
                            wind_speed = EXCLUDED.wind_speed,
                            solar_generation = EXCLUDED.solar_generation,
                            cloud_cover = EXCLUDED.cloud_cover,
                            is_holiday = EXCLUDED.is_holiday
                    """)
                
                conn.execute(query, row_dict)
                rows_inserted += 1
        
        logger.info(f"Inserted/updated {rows_inserted} rows in hourly_actuals")
        return rows_inserted
    
    def get_latest_timestamp(self) -> Optional[datetime]:
        """Get the timestamp of the most recent data point."""
        query = text("SELECT MAX(ts) as max_ts FROM hourly_actuals")
        
        with self.engine.connect() as conn:
            result = conn.execute(query).fetchone()
            if result and result[0]:
                # Convert string to datetime if needed (SQLite returns string)
                ts = result[0]
                if isinstance(ts, str):
                    return pd.to_datetime(ts).to_pydatetime()
                return ts
            return None
    
    def get_row_count(self) -> int:
        """Get total number of rows in hourly_actuals."""
        query = text("SELECT COUNT(*) FROM hourly_actuals")
        
        with self.engine.connect() as conn:
            result = conn.execute(query).fetchone()
            return result[0] if result else 0
    
    def initialize_schema(self):
        """Create tables if they don't exist."""
        schema_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'db', 'schema.sql'
        )
        
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            with self.engine.begin() as conn:
                # Execute each statement separately
                for statement in schema_sql.split(';'):
                    statement = statement.strip()
                    if statement:
                        conn.execute(text(statement))
            
            logger.info("Database schema initialized")
        else:
            logger.warning(f"Schema file not found at {schema_path}")


# Global instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get or create the global storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
        _storage_service.initialize_schema()
    return _storage_service
