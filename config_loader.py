"""
Drainfield Configuration Loader
Handles loading and filtering drainfield JSON configurations
"""

import json
import os
from pathlib import Path


class ConfigLoader:
    """Manages loading and caching of drainfield configuration files"""
    
    def __init__(self, json_dir=r"C:\drainfield_generator\json"):
        """
        Initialize the configuration loader
        
        Args:
            json_dir: Directory containing the JSON configuration files
        """
        self.json_dir = Path(json_dir)
        self.configs = {}
        
    def load_all_configs(self):
        """Load all 6 configuration files at startup"""
        products = ['mps9', 'arc24', 'eq36lp']
        config_types = ['bed', 'trench']
        
        print("Loading drainfield configurations...")
        for product in products:
            for config_type in config_types:
                filename = f"{product}_{config_type}.json"
                filepath = self.json_dir / filename
                
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        key = f"{product}_{config_type}"
                        self.configs[key] = data
                        print(f"  ✓ Loaded {filename} ({len(data)} configurations)")
                except FileNotFoundError:
                    print(f"  ✗ Warning: {filename} not found")
                except json.JSONDecodeError as e:
                    print(f"  ✗ Error parsing {filename}: {e}")
        
        return len(self.configs) == 6
    
    def get_configs(self, product, config_type):
        """
        Get configurations for a specific product and type
        
        Args:
            product: 'mps9', 'arc24', or 'eq36lp'
            config_type: 'bed' or 'trench'
            
        Returns:
            Dictionary of configurations or empty dict if not found
        """
        key = f"{product}_{config_type}"
        return self.configs.get(key, {})
    
    def filter_by_size(self, configs, min_sqft):
        """
        Filter configurations that meet minimum square footage
        
        Args:
            configs: Dictionary of configuration data
            min_sqft: Minimum required square footage
            
        Returns:
            List of (pattern_key, config_data) tuples that meet requirements
        """
        candidates = []
        
        for pattern_key, config_data in configs.items():
            credit_sqft = config_data['metadata']['credit_sqft']
            if credit_sqft >= min_sqft:
                candidates.append((pattern_key, config_data))
        
        return candidates
    
    def sort_candidates(self, candidates):
        """
        Sort candidates by priority: rectangular first, then smallest size
        
        Args:
            candidates: List of (pattern_key, config_data) tuples
            
        Returns:
            Sorted list of candidates
        """
        return sorted(candidates, key=lambda x: (
            not x[1]['metadata']['is_rectangular'],  # False (rectangular) sorts first
            x[1]['metadata']['credit_sqft']  # Then by size
        ))
    
    def get_product_specs(self, product):
        """
        Get the physical specifications for a product
        
        Args:
            product: 'mps9', 'arc24', or 'eq36lp'
            
        Returns:
            Dictionary with width, height, and credit_per_piece
        """
        specs = {
            'mps9': {
                'width': 2.0,
                'height': 10.0,
                'credit_per_piece': 30.0
            },
            'arc24': {
                'width': 1.8333,
                'height': 5.0,
                'credit_per_piece': 15.0
            },
            'eq36lp': {
                'width': 1.8333,
                'height': 4.0,
                'credit_per_piece': 11.32
            }
        }
        return specs.get(product, {})
