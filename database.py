"""
Database Module
Handles PostgreSQL database connections and updates for septic system data
"""

import psycopg2
from psycopg2 import sql
import os


class SepticDatabase:
    """Handles database operations for septic system records"""

    def __init__(self, db_config=None):
        """
        Initialize database connection

        Args:
            db_config: Dictionary with connection parameters
                      (host, database, user, password, port)
                      If None, reads from environment variables
        """
        self.db_config = db_config or self._get_default_config()
        self.connection = None

    def _get_default_config(self):
        """Get database config from environment variables"""
        return {
            'host': os.getenv('DB_HOST', '127.0.0.1'),
            'database': os.getenv('DB_NAME', 'redbayengineering'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', '197420162018'),
            'port': os.getenv('DB_PORT', '5432')
        }

    def connect(self):
        """
        Establish database connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.connection = psycopg2.connect(**self.db_config)
            return True
        except psycopg2.Error as e:
            print(f"Database connection error: {e}")
            return False

    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None

    def update_septic_system_record(self,
                                    property_id,
                                    net_acreage,
                                    flow_gpd,
                                    authorized_flow,
                                    gpd_multiplier,
                                    unobstructed_area_available,
                                    unobstructed_area_required,
                                    benchmark_text=None,
                                    rate=None,
                                    is_trench=False,
                                    is_bed=False):
        """
        Update septic system record in p3ofdep4015 table

        Args:
            property_id: Property ID (page3_06)
            net_acreage: Net acreage (page3_09)
            flow_gpd: Total estimated sewage flow (page3_10)
            authorized_flow: Authorized sewage flow (page3_12)
            gpd_multiplier: GPD multiplier - "1500" or "2500" (page3_13)
            unobstructed_area_available: Available area from boundary (page3_14)
            unobstructed_area_required: Required unobstructed area (page3_15)
            benchmark_text: Optional benchmark description (page3_16)
            rate: Drainfield rate - "0.6/Sand" or "0.8/Sand" (page3_121)
            is_trench: Boolean for trench configuration (page3_123)
            is_bed: Boolean for bed configuration (page3_124)

        Returns:
            True if update successful, False otherwise
        """
        if not self.connection:
            if not self.connect():
                return False

        try:
            with self.connection.cursor() as cursor:
                # Build update query
                update_query = sql.SQL("""
                    UPDATE "p3ofdep4015"
                    SET "page3_09" = %s,
                        "page3_10" = %s,
                        "page3_12" = %s,
                        "page3_13" = %s,
                        "page3_14" = %s,
                        "page3_15" = %s,
                        "page3_16" = %s,
                        "page3_121" = %s,
                        "page3_123" = %s,
                        "page3_124" = %s
                    WHERE "page3_06" = %s
                """)

                cursor.execute(update_query, (
                    net_acreage,
                    flow_gpd,
                    authorized_flow,
                    str(gpd_multiplier),  # Stored as varchar
                    unobstructed_area_available,
                    unobstructed_area_required,
                    benchmark_text,
                    rate,
                    is_trench,
                    is_bed,
                    property_id
                ))

                self.connection.commit()
                return True

        except psycopg2.Error as e:
            print(f"Database update error: {e}")
            self.connection.rollback()
            return False

    def get_benchmark_and_core_data(self, property_id):
        """
        Retrieve benchmark and core data from database

        Args:
            property_id: Property ID (page3_06)

        Returns:
            Dictionary with benchmark, core_depth, and core_above_below
            or None if not found or error
        """
        if not self.connection:
            if not self.connect():
                return None

        try:
            with self.connection.cursor() as cursor:
                query = sql.SQL("""
                    SELECT "page3_16", "page3_17", "page3_19"
                    FROM "p3ofdep4015"
                    WHERE "page3_06" = %s
                """)

                cursor.execute(query, (property_id,))
                result = cursor.fetchone()

                if result:
                    benchmark_text = result[0]
                    core_depth = result[1]
                    core_above_below_bool = result[2]

                    # Convert boolean to ABOVE/BELOW
                    if core_above_below_bool is not None:
                        core_above_below = "ABOVE" if core_above_below_bool else "BELOW"
                    else:
                        core_above_below = None

                    return {
                        'benchmark_text': benchmark_text,
                        'core_depth': core_depth,
                        'core_above_below': core_above_below
                    }

                return None

        except psycopg2.Error as e:
            print(f"Database query error: {e}")
            return None

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# Convenience function
def update_septic_record(property_id, **kwargs):
    """
    Quick function to update septic system record

    Args:
        property_id: Property ID
        **kwargs: All fields to update

    Returns:
        True if successful, False otherwise
    """
    with SepticDatabase() as db:
        return db.update_septic_system_record(property_id, **kwargs)
