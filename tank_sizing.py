"""
Tank Sizing Module
Determines septic tank and ATU requirements based on flow
"""

import csv
import math
from pathlib import Path


class TankSizer:
    """Handles tank sizing calculations based on FDEP regulations"""

    def __init__(self, data_dir="data"):
        """
        Initialize tank sizer with tank sizing data

        Args:
            data_dir: Directory containing CSV data files
        """
        self.data_dir = Path(data_dir)
        self.tank_data = []
        self._load_data()

    def _load_data(self):
        """Load tank sizing data from CSV"""
        csv_path = self.data_dir / "fdep_tank_sizing.csv"

        if not csv_path.exists():
            raise FileNotFoundError(f"Tank sizing data not found at {csv_path}")

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tank_data.append({
                    'min_flow_gpd': int(row['min_flow_gpd']),
                    'max_flow_gpd': int(row['max_flow_gpd']),
                    'septic_tank_min_capacity': int(row['septic_tank_min_capacity']),
                    'pump_tank_min_residential': int(row['pump_tank_min_residential']),
                    'pump_tank_min_commercial': int(row['pump_tank_min_commercial'])
                })

    def get_septic_tank_size(self, flow_gpd, num_homes=1):
        """
        Get required septic tank size based on flow

        Args:
            flow_gpd: Sewage flow in gallons per day
            num_homes: Number of dwelling units (adds 75 gallons per extra home)

        Returns:
            Required septic tank capacity in gallons
        """
        # Find matching flow range
        for tank_range in self.tank_data:
            if tank_range['min_flow_gpd'] <= flow_gpd <= tank_range['max_flow_gpd']:
                base_capacity = tank_range['septic_tank_min_capacity']

                # Add 75 gallons per additional dwelling unit
                if num_homes > 1:
                    additional_gallons = num_homes * 75
                    return base_capacity + additional_gallons

                return base_capacity

        # If flow exceeds max in table, return highest capacity
        if flow_gpd > self.tank_data[-1]['max_flow_gpd']:
            base_capacity = self.tank_data[-1]['septic_tank_min_capacity']
            if num_homes > 1:
                additional_gallons = num_homes * 75
                return base_capacity + additional_gallons
            return base_capacity

        # Default fallback
        return 900

    def get_pump_tank_size(self, flow_gpd, is_residential=True):
        """
        Get required pump tank size based on flow

        Args:
            flow_gpd: Sewage flow in gallons per day
            is_residential: True for residential, False for commercial

        Returns:
            Required pump tank capacity in gallons
        """
        # Find matching flow range
        for tank_range in self.tank_data:
            if tank_range['min_flow_gpd'] <= flow_gpd <= tank_range['max_flow_gpd']:
                if is_residential:
                    return tank_range['pump_tank_min_residential']
                else:
                    return tank_range['pump_tank_min_commercial']

        # If flow exceeds max in table, return highest capacity
        if flow_gpd > self.tank_data[-1]['max_flow_gpd']:
            if is_residential:
                return self.tank_data[-1]['pump_tank_min_residential']
            else:
                return self.tank_data[-1]['pump_tank_min_commercial']

        # Default fallback
        return 150 if is_residential else 225

    def calculate_atu_size(self, bedrooms, square_footage, flow_gpd, is_residential=True):
        """
        Calculate required ATU (Aerobic Treatment Unit) size

        Args:
            bedrooms: Number of bedrooms
            square_footage: Building square footage
            flow_gpd: Sewage flow in gallons per day
            is_residential: True for residential, False for commercial

        Returns:
            Required ATU capacity in gallons
        """
        if is_residential:
            # Residential ATU sizing based on bedrooms and square footage
            if (bedrooms <= 2 and square_footage <= 1200) or \
               (bedrooms == 3 and square_footage <= 2250):
                return 400

            if bedrooms == 4 and square_footage <= 3300:
                return 500

            # For larger homes, use the greater of area-based or bedroom-based calculation
            if square_footage > 3300:
                area_gallons = 500 + (math.ceil((square_footage - 3300) / 750) * 60)
            else:
                area_gallons = 500

            if bedrooms > 4:
                bedroom_gallons = 500 + ((bedrooms - 4) * 60)
            else:
                bedroom_gallons = 500

            return max(area_gallons, bedroom_gallons)

        else:
            # Commercial ATU sizing based on flow
            if 0 <= flow_gpd <= 400:
                return 400
            elif 401 <= flow_gpd <= 500:
                return 500
            elif 501 <= flow_gpd <= 600:
                return 600
            elif 601 <= flow_gpd <= 700:
                return 700
            elif 701 <= flow_gpd <= 750:
                return 750
            elif 751 <= flow_gpd <= 800:
                return 800
            elif 801 <= flow_gpd <= 1000:
                return 1000
            elif 1001 <= flow_gpd <= 1200:
                return 1200
            elif 1201 <= flow_gpd <= 1500:
                return 1500
            else:
                # Flow exceeds supported range
                return None


# Convenience functions
def get_tank_requirements(flow_gpd, num_homes=1, data_dir="data"):
    """
    Quick function to get tank requirements

    Args:
        flow_gpd: Sewage flow in gallons per day
        num_homes: Number of dwelling units
        data_dir: Directory containing data files

    Returns:
        Dictionary with tank sizing information
    """
    sizer = TankSizer(data_dir)
    return {
        'septic_tank': sizer.get_septic_tank_size(flow_gpd, num_homes),
        'pump_tank_residential': sizer.get_pump_tank_size(flow_gpd, True),
        'pump_tank_commercial': sizer.get_pump_tank_size(flow_gpd, False)
    }
