"""
Drainfield Requirements Module
Provides drainfield sizing requirements based on flow and configuration type
"""

import csv
from pathlib import Path


class DrainFieldRequirements:
    """Handles drainfield requirement lookups"""

    def __init__(self, data_dir="data"):
        """
        Initialize with drainfield requirements data

        Args:
            data_dir: Directory containing CSV data files
        """
        self.data_dir = Path(data_dir)
        self.requirements = {}
        self._load_data()

    def _load_data(self):
        """Load drainfield requirements from CSV"""
        csv_path = self.data_dir / "fdep_drainfield_configs.csv"

        if not csv_path.exists():
            raise FileNotFoundError(f"Drainfield config data not found at {csv_path}")

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                flow_gpd = int(row['flow_gpd'])
                config_name = row['configuration_name'].strip()
                drainfield_size = int(row['drainfield_size'])
                unobstructed_area = int(row['unobstructed_area'])

                # Create key from flow and config name
                key = (flow_gpd, config_name)
                self.requirements[key] = {
                    'drainfield_size': drainfield_size,
                    'unobstructed_area': unobstructed_area
                }

    def get_requirements(self, flow_gpd, config_type):
        """
        Get drainfield requirements for given flow and configuration

        Args:
            flow_gpd: Sewage flow in gallons per day
            config_type: Configuration type (e.g., 'trench', 'bed', 'trench_atu')

        Returns:
            Dictionary with drainfield_size and unobstructed_area, or None if not found
        """
        # Map config_type to CSV configuration_name
        config_map = {
            'trench': 'Trench',
            'bed': 'Bed',
            'trench_atu': 'Trench with ATU',
            'bed_atu': 'Bed with ATU',
            'split_trench': 'Trench split in half',
            'split_bed': 'Bed split in half',
            'split_trench_atu': 'Trench split in half with ATU',
            'split_bed_atu': 'Bed split in half with ATU'
        }

        config_name = config_map.get(config_type)
        if not config_name:
            return None

        # Try exact match first
        key = (flow_gpd, config_name)
        if key in self.requirements:
            return self.requirements[key]

        # If not found, find closest flow_gpd (round up)
        available_flows = sorted(set(k[0] for k in self.requirements.keys()))

        # Find the next higher flow rate
        for available_flow in available_flows:
            if available_flow >= flow_gpd:
                key = (available_flow, config_name)
                if key in self.requirements:
                    return self.requirements[key]

        # If still not found, use highest available
        if available_flows:
            key = (available_flows[-1], config_name)
            if key in self.requirements:
                return self.requirements[key]

        return None


# Convenience function
def get_drainfield_requirements(flow_gpd, config_type, data_dir="data"):
    """
    Quick function to get drainfield requirements

    Args:
        flow_gpd: Sewage flow in gallons per day
        config_type: Configuration type
        data_dir: Directory containing data files

    Returns:
        Dictionary with requirements or None
    """
    req = DrainFieldRequirements(data_dir)
    return req.get_requirements(flow_gpd, config_type)
