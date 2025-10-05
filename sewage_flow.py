"""
Sewage Flow Calculation Module
Calculates gallons per day (GPD) based on bedrooms and square footage
"""

import csv
import math
from pathlib import Path


class SewageFlowCalculator:
    """Handles sewage flow calculations based on FDEP regulations"""

    def __init__(self, data_dir="data"):
        """
        Initialize calculator with sewage flow data

        Args:
            data_dir: Directory containing CSV data files
        """
        self.data_dir = Path(data_dir)
        self.flow_data = {}
        self._load_data()

    def _load_data(self):
        """Load sewage flow data from CSV"""
        csv_path = self.data_dir / "fdep_sewage_flows.csv"

        if not csv_path.exists():
            raise FileNotFoundError(f"Sewage flow data not found at {csv_path}")

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                bedrooms = int(row['bedrooms'])
                sqft_min = int(row['square_footage_min'])
                sqft_max = int(row['square_footage_max'])
                flow_gpd = int(row['flow_gpd'])

                if bedrooms not in self.flow_data:
                    self.flow_data[bedrooms] = []

                self.flow_data[bedrooms].append({
                    'sqft_min': sqft_min,
                    'sqft_max': sqft_max,
                    'flow_gpd': flow_gpd
                })

    def calculate_flow(self, bedrooms, square_footage):
        """
        Calculate sewage flow in gallons per day (GPD)

        Args:
            bedrooms: Number of bedrooms
            square_footage: Building square footage

        Returns:
            Sewage flow in GPD

        Raises:
            ValueError: If bedrooms count is not in data
        """
        if bedrooms not in self.flow_data:
            raise ValueError(f"No data available for {bedrooms} bedrooms")

        # Find matching range
        for range_data in self.flow_data[bedrooms]:
            if range_data['sqft_min'] <= square_footage <= range_data['sqft_max']:
                return range_data['flow_gpd']

        # Handle overflow (building larger than max in table)
        # Find the last (largest) range for this bedroom count
        last_range = max(self.flow_data[bedrooms], key=lambda x: x['sqft_max'])
        max_sqft = last_range['sqft_max']
        base_flow = last_range['flow_gpd']

        if square_footage > max_sqft:
            # Add 60 GPD for each additional 750 sqft
            additional_sqft = square_footage - max_sqft
            additional_units = math.ceil(additional_sqft / 750)
            additional_flow = additional_units * 60

            return base_flow + additional_flow

        # Should not reach here, but return base flow as fallback
        return base_flow

    def get_flow_range(self, bedrooms, square_footage):
        """
        Get the flow range information for given parameters

        Args:
            bedrooms: Number of bedrooms
            square_footage: Building square footage

        Returns:
            Dictionary with range info and calculated flow
        """
        flow_gpd = self.calculate_flow(bedrooms, square_footage)

        # Find the range this falls into
        for range_data in self.flow_data[bedrooms]:
            if range_data['sqft_min'] <= square_footage <= range_data['sqft_max']:
                return {
                    'flow_gpd': flow_gpd,
                    'sqft_min': range_data['sqft_min'],
                    'sqft_max': range_data['sqft_max'],
                    'is_overflow': False
                }

        # It's an overflow calculation
        last_range = max(self.flow_data[bedrooms], key=lambda x: x['sqft_max'])
        return {
            'flow_gpd': flow_gpd,
            'sqft_min': last_range['sqft_max'] + 1,
            'sqft_max': square_footage,
            'is_overflow': True
        }


# Convenience function for quick calculations
def calculate_sewage_flow(bedrooms, square_footage, data_dir="data"):
    """
    Quick function to calculate sewage flow

    Args:
        bedrooms: Number of bedrooms
        square_footage: Building square footage
        data_dir: Directory containing data files

    Returns:
        Sewage flow in GPD
    """
    calculator = SewageFlowCalculator(data_dir)
    return calculator.calculate_flow(bedrooms, square_footage)
