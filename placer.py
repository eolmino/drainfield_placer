"""
Drainfield Placement Module
Handles placing drainfield configurations into CAD JSON
"""

import copy
from shapely.affinity import translate, rotate
import math


def translate_point(point, dx, dy):
    """
    Translate a CAD point by offset
    
    Args:
        point: Dictionary with 'x' and 'y' keys
        dx: X offset
        dy: Y offset
        
    Returns:
        New point dictionary
    """
    return {
        'x': point['x'] + dx,
        'y': point['y'] + dy
    }


def rotate_point(point, angle_deg, origin_x, origin_y):
    """
    Rotate a point around an origin
    
    Args:
        point: Dictionary with 'x' and 'y'
        angle_deg: Rotation angle in degrees
        origin_x, origin_y: Rotation origin
        
    Returns:
        Rotated point dictionary
    """
    angle_rad = math.radians(angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    
    # Translate to origin
    x = point['x'] - origin_x
    y = point['y'] - origin_y
    
    # Rotate
    x_rot = x * cos_a - y * sin_a
    y_rot = x * sin_a + y * cos_a
    
    # Translate back
    return {
        'x': x_rot + origin_x,
        'y': y_rot + origin_y
    }


def transform_polyline(polyline, rotation, origin_x, origin_y, dx, dy):
    """
    Transform a polyline (rotate then translate)
    
    Args:
        polyline: CAD polyline dictionary
        rotation: Rotation angle in degrees
        origin_x, origin_y: Rotation origin (usually centroid)
        dx, dy: Translation offset
        
    Returns:
        Transformed polyline dictionary
    """
    transformed = copy.deepcopy(polyline)
    
    # First rotate if needed
    if rotation != 0:
        transformed['points'] = [
            rotate_point(pt, rotation, origin_x, origin_y)
            for pt in transformed['points']
        ]
    
    # Then translate
    transformed['points'] = [
        translate_point(pt, dx, dy)
        for pt in transformed['points']
    ]
    
    return transformed


def calculate_polygon_centroid(points):
    """
    Calculate centroid of a polygon
    
    Args:
        points: List of point dictionaries with 'x' and 'y'
        
    Returns:
        Tuple of (centroid_x, centroid_y)
    """
    n = len(points)
    if n == 0:
        return (0, 0)
    
    cx = sum(pt['x'] for pt in points) / n
    cy = sum(pt['y'] for pt in points) / n
    
    return (cx, cy)


def place_drainfield(base_cad_json, selection_result):
    """
    Place the selected drainfield configuration into CAD JSON
    
    Args:
        base_cad_json: Original CAD JSON structure
        selection_result: Result dictionary from selector
        
    Returns:
        Modified CAD JSON with drainfield added
    """
    # Deep copy to avoid modifying original
    output_cad = copy.deepcopy(base_cad_json)
    
    # Ensure polylines array exists
    if 'polylines' not in output_cad:
        output_cad['polylines'] = []
    
    # Get the drainfield configuration
    config_data = selection_result['config_data']
    rotation = selection_result['rotation']
    dx = selection_result['offset_x']
    dy = selection_result['offset_y']
    
    # Get polylines from config
    drainfield_polylines = config_data['cad_json']['polylines']
    
    # Find shoulder polyline to get centroid (rotation origin)
    shoulder = None
    for polyline in drainfield_polylines:
        if polyline.get('closed', False):
            shoulder = polyline
            break
    
    if shoulder:
        origin_x, origin_y = calculate_polygon_centroid(shoulder['points'])
    else:
        origin_x, origin_y = 0, 0
    
    # Transform and add each polyline
    for polyline in drainfield_polylines:
        transformed = transform_polyline(
            polyline,
            rotation,
            origin_x,
            origin_y,
            dx,
            dy
        )
        
        # Add metadata about the placement
        transformed['metadata'] = {
            'source': 'drainfield_placer',
            'product': selection_result['product'],
            'pattern': selection_result['pattern_key'],
            'rotation': rotation,
            'is_shoulder': polyline.get('closed', False)
        }
        
        output_cad['polylines'].append(transformed)
    
    return output_cad


def place_split_drainfield(base_cad_json, selection_result):
    """
    Place a split drainfield system into CAD JSON
    
    Args:
        base_cad_json: Original CAD JSON structure
        selection_result: Split system result dictionary
        
    Returns:
        Modified CAD JSON with both drainfields added
    """
    # Start with base
    output_cad = copy.deepcopy(base_cad_json)
    
    # Place first drainfield
    output_cad = place_drainfield(output_cad, selection_result['drainfield_1'])
    
    # Place second drainfield
    output_cad = place_drainfield(output_cad, selection_result['drainfield_2'])
    
    return output_cad


def create_placement_summary(selection_result):
    """
    Create a human-readable summary of the placement
    
    Args:
        selection_result: Result dictionary from selector
        
    Returns:
        Dictionary with formatted summary information
    """
    if not selection_result['success']:
        return {
            'status': 'FAILED',
            'reason': selection_result.get('reason', 'unknown'),
            'message': selection_result.get('message', 'Configuration could not be placed'),
            'attempted': selection_result.get('attempted', [])
        }
    
    # Handle split systems
    if selection_result.get('is_split', False):
        df1 = selection_result['drainfield_1']
        df2 = selection_result['drainfield_2']
        
        return {
            'status': 'SUCCESS (SPLIT SYSTEM)',
            'config_type': selection_result['config_type'],
            'flow_gpd': selection_result.get('flow_gpd', 'N/A'),
            'required_sqft_each': selection_result.get('required_sqft_each', 'N/A'),
            'drainfield_1': {
                'product': df1['product'].upper(),
                'pattern': df1['pattern_key'],
                'credit_sqft': df1['metadata']['credit_sqft'],
                'num_pieces': df1['metadata']['num_pieces'],
                'rotation': df1['rotation']
            },
            'drainfield_2': {
                'product': df2['product'].upper(),
                'pattern': df2['pattern_key'],
                'credit_sqft': df2['metadata']['credit_sqft'],
                'num_pieces': df2['metadata']['num_pieces'],
                'rotation': df2['rotation']
            },
            'attempted': selection_result.get('attempted', [])
        }
    
    # Standard single drainfield
    return {
        'status': 'SUCCESS',
        'product': selection_result['product'].upper(),
        'config_type': selection_result['config_type'],
        'pattern': selection_result['pattern_key'],
        'credit_sqft': selection_result['metadata']['credit_sqft'],
        'num_pieces': selection_result['metadata']['num_pieces'],
        'is_rectangular': selection_result['metadata']['is_rectangular'],
        'rotation': selection_result['rotation'],
        'offset_x': round(selection_result['offset_x'], 2),
        'offset_y': round(selection_result['offset_y'], 2),
        'flow_gpd': selection_result.get('flow_gpd', 'N/A'),
        'required_sqft': selection_result.get('required_sqft', 'N/A'),
        'attempted': selection_result.get('attempted', [])
    }
