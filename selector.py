"""
Drainfield Selection Module
Implements the configuration selection hierarchy
"""

import math
from geometry import (
    extract_shoulder_polygon,
    polygon_fits,
    try_rotations,
    calculate_centroid_offset
)


class DrainFieldSelector:
    """Handles drainfield configuration selection based on hierarchy"""
    
    def __init__(self, config_loader):
        """
        Initialize selector with configuration loader
        
        Args:
            config_loader: Instance of ConfigLoader
        """
        self.config_loader = config_loader
        self.product_priority = ['mps9', 'arc24', 'eq36lp']
    
    def calculate_required_sqft(self, flow_gpd, config_type):
        """
        Calculate required square footage based on flow and configuration type
        
        Args:
            flow_gpd: Gallons per day flow rate
            config_type: 'trench', 'bed', 'trench_atu', or 'bed_atu'
            
        Returns:
            Required square footage (rounded up)
        """
        # Base calculations
        if 'trench' in config_type:
            base_sqft = flow_gpd / 0.8
        else:  # bed
            base_sqft = flow_gpd / 0.6
        
        # Apply ATU reduction if applicable
        if 'atu' in config_type:
            base_sqft = base_sqft * 0.75
        
        return math.ceil(base_sqft)
    
    def select_configuration(self, user_boundary, required_sqft, config_type='trench'):
        """
        Select the best drainfield configuration for given requirements
        
        Args:
            user_boundary: Shapely Polygon of user-drawn boundary
            required_sqft: Required square footage
            config_type: 'trench', 'bed', 'trench_atu', or 'bed_atu'
            
        Returns:
            Dictionary with selection results
        """
        # Extract base type (trench or bed)
        base_type = 'trench' if 'trench' in config_type else 'bed'
        
        # Try each product in priority order
        for product in self.product_priority:
            result = self._try_product(
                product, 
                base_type, 
                user_boundary, 
                required_sqft
            )
            
            if result['success']:
                result['config_type'] = config_type
                return result
        
        # Nothing fit
        return {
            'success': False,
            'reason': f'no_fit_{config_type}',
            'config_type': config_type
        }
    
    def _try_product(self, product, config_type, user_boundary, required_sqft):
        """
        Try all configurations for a specific product
        
        Args:
            product: 'mps9', 'arc24', or 'eq36lp'
            config_type: 'trench' or 'bed'
            user_boundary: Shapely Polygon
            required_sqft: Required square footage
            
        Returns:
            Dictionary with success status and details
        """
        # Get configurations for this product/type
        configs = self.config_loader.get_configs(product, config_type)
        
        if not configs:
            return {'success': False}
        
        # Filter by size
        candidates = self.config_loader.filter_by_size(configs, required_sqft)
        
        if not candidates:
            return {'success': False}
        
        # Sort: rectangular first, then smallest
        sorted_candidates = self.config_loader.sort_candidates(candidates)
        
        # Try each candidate with rotation
        for pattern_key, config_data in sorted_candidates:
            # Extract shoulder polygon
            try:
                shoulder_polygon = extract_shoulder_polygon(config_data)
            except Exception as e:
                print(f"Warning: Could not extract polygon for {pattern_key}: {e}")
                continue
            
            # Try rotations to find a fit
            fits, rotation_angle, fitted_polygon = try_rotations(
                shoulder_polygon,
                user_boundary
            )

            if fits:
                # Calculate placement offset from original position to boundary
                # Note: fitted_polygon is already positioned, but we need the offset
                # from the ORIGINAL shoulder_polygon to apply in placer.py
                boundary_centroid = user_boundary.centroid
                original_centroid = shoulder_polygon.centroid
                dx = boundary_centroid.x - original_centroid.x
                dy = boundary_centroid.y - original_centroid.y

                return {
                    'success': True,
                    'product': product,
                    'pattern_key': pattern_key,
                    'config_data': config_data,
                    'metadata': config_data['metadata'],
                    'rotation': rotation_angle,
                    'offset_x': dx,
                    'offset_y': dy,
                    'fitted_polygon': fitted_polygon
                }
        
        return {'success': False}
    
    def apply_hierarchy(self, user_boundary, flow_gpd, split_boundaries=None):
        """
        Apply the complete selection hierarchy
        
        Hierarchy:
        1. TRENCH (standard)
        2. BED (standard)
        3. TRENCH + ATU (25% reduction)
        4. BED + ATU (25% reduction)
        5. RETURN: needs_split
        6. SPLIT + TRENCH (50% each)
        7. SPLIT + BED (50% each)
        8. SPLIT + TRENCH + ATU (50% + 25% reduction)
        9. SPLIT + BED + ATU (50% + 25% reduction)
        10. RETURN: needs_redesign
        
        Args:
            user_boundary: Shapely Polygon (or list of 2 for split)
            flow_gpd: Gallons per day
            split_boundaries: Optional list of 2 boundaries for split system
            
        Returns:
            Dictionary with final selection or failure reason
        """
        attempted = []
        
        # Standard configurations (1-4)
        hierarchy_standard = [
            ('trench', 1.0),
            ('bed', 1.0),
            ('trench_atu', 0.75),
            ('bed_atu', 0.75)
        ]
        
        for config_type, multiplier in hierarchy_standard:
            required_sqft = self.calculate_required_sqft(flow_gpd, config_type)
            
            result = self.select_configuration(
                user_boundary, 
                required_sqft, 
                config_type
            )
            
            attempted.append(config_type)
            
            if result['success']:
                result['attempted'] = attempted
                result['flow_gpd'] = flow_gpd
                result['required_sqft'] = required_sqft
                return result
        
        # If we get here, we need a split system (step 5)
        if split_boundaries is None:
            return {
                'success': False,
                'reason': 'needs_split',
                'attempted': attempted,
                'message': 'No configuration fits in single boundary. Please create two boundaries for split system.'
            }
        
        # Split configurations (6-9)
        if len(split_boundaries) != 2:
            return {
                'success': False,
                'reason': 'invalid_split',
                'message': 'Split system requires exactly 2 boundaries.'
            }
        
        hierarchy_split = [
            ('trench', 1.0),
            ('bed', 1.0),
            ('trench_atu', 0.75),
            ('bed_atu', 0.75)
        ]
        
        for config_type, multiplier in hierarchy_split:
            # Each boundary gets 50% of requirement
            required_sqft = self.calculate_required_sqft(flow_gpd, config_type) // 2
            
            results = []
            for i, boundary in enumerate(split_boundaries):
                result = self.select_configuration(
                    boundary,
                    required_sqft,
                    f"split_{config_type}"
                )
                
                if result['success']:
                    result['split_index'] = i
                    results.append(result)
            
            attempted.append(f"split_{config_type}")
            
            # Both boundaries must fit
            if len(results) == 2:
                return {
                    'success': True,
                    'is_split': True,
                    'config_type': f"split_{config_type}",
                    'drainfield_1': results[0],
                    'drainfield_2': results[1],
                    'attempted': attempted,
                    'flow_gpd': flow_gpd,
                    'required_sqft_each': required_sqft
                }
        
        # Nothing worked (step 10)
        return {
            'success': False,
            'reason': 'needs_redesign',
            'attempted': attempted,
            'message': 'No configuration fits even with split system. Architect intervention required.'
        }
