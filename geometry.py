"""
Geometry Operations Module - UPDATED
Handles all Shapely-based geometric operations for drainfield placement
WITH EDGE ALIGNMENT AND STRICT FIT CHECKING
"""

from shapely.geometry import Polygon, LineString
from shapely.affinity import translate, rotate
import math


def extract_shoulder_polygon(config):
    """
    Extract the shoulder boundary polygon from a configuration
    
    Args:
        config: Configuration dictionary with cad_json data
        
    Returns:
        Shapely Polygon representing the shoulder boundary
    """
    polylines = config['cad_json']['polylines']
    
    # Find the closed polyline (shoulder boundary - should be last one)
    shoulder = None
    for polyline in polylines:
        if polyline.get('closed', False):
            shoulder = polyline
            break
    
    if not shoulder:
        raise ValueError("No closed shoulder boundary found in configuration")
    
    # Extract points and create polygon
    points = [(pt['x'], pt['y']) for pt in shoulder['points']]
    return Polygon(points)


def parse_user_boundary(cad_json, boundary_layer_name='polyline_boundary'):
    """
    Extract user-drawn boundary from CAD JSON
    
    Args:
        cad_json: CAD JSON data structure
        boundary_layer_name: Name of the layer containing the boundary
        
    Returns:
        Shapely Polygon representing the user boundary
    """
    # Find polylines on the boundary layer
    boundary_polylines = []
    
    for polyline in cad_json.get('polylines', []):
        if polyline.get('layer') == boundary_layer_name:
            boundary_polylines.append(polyline)
    
    if not boundary_polylines:
        raise ValueError(f"No boundary found on layer '{boundary_layer_name}'")
    
    if len(boundary_polylines) > 1:
        print(f"Warning: Multiple polylines found on boundary layer. Using first one.")
    
    # Use the first boundary polyline
    boundary = boundary_polylines[0]
    points = [(pt['x'], pt['y']) for pt in boundary['points']]
    
    return Polygon(points)


def polygon_fits(drainfield_polygon, user_boundary, tolerance=0.001):
    """
    STRICT fit check - drainfield must be fully within boundary
    
    Args:
        drainfield_polygon: Shapely Polygon of drainfield shoulder
        user_boundary: Shapely Polygon of user-drawn boundary
        tolerance: Small buffer for floating-point precision (0.001 sq ft = ~0.14 inches)
        
    Returns:
        Boolean indicating if it fits
    """
    # Check if completely within
    if drainfield_polygon.within(user_boundary):
        return True
    
    # Allow tiny overlap due to floating point precision
    if drainfield_polygon.intersects(user_boundary):
        overlap_area = drainfield_polygon.difference(user_boundary).area
        if overlap_area < tolerance:
            return True
    
    return False


def get_boundary_edge_angles(boundary_polygon):
    """
    Get the angles of all edges in the boundary polygon
    
    Args:
        boundary_polygon: Shapely Polygon
        
    Returns:
        List of angles in degrees (0-180)
    """
    coords = list(boundary_polygon.exterior.coords)
    angles = []
    
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i + 1]
        
        # Calculate angle of this edge
        dx = x2 - x1
        dy = y2 - y1
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        
        # Normalize to 0-180 (parallel edges should have same angle)
        if angle_deg < 0:
            angle_deg += 180
        
        # Get edge length
        length = math.sqrt(dx*dx + dy*dy)
        
        angles.append((angle_deg, length, i))
    
    return angles


def try_edge_aligned_rotations(drainfield_polygon, user_boundary):
    """
    Try rotating drainfield to align with boundary edges
    Also tries 0, 90, 180, 270 degrees (cardinal directions)

    Args:
        drainfield_polygon: Shapely Polygon of drainfield
        user_boundary: Shapely Polygon of user boundary

    Returns:
        Tuple of (fits: bool, rotation_angle: float, rotated_polygon: Polygon)
    """
    # Get boundary edge angles
    edge_angles = get_boundary_edge_angles(user_boundary)

    # Sort by edge length (try longest edges first)
    edge_angles.sort(key=lambda x: x[1], reverse=True)

    # Collect rotation angles to try
    rotation_angles = set()

    # Add boundary edge angles
    for angle, length, idx in edge_angles:
        rotation_angles.add(angle)
        rotation_angles.add(angle + 90)  # Perpendicular to edge

    # Add cardinal directions
    rotation_angles.update([0, 90, 180, 270])

    # Add fine-tuning around boundary edges (±5 degrees)
    extra_angles = set()
    for angle in list(rotation_angles):
        extra_angles.add(angle - 5)
        extra_angles.add(angle + 5)
    rotation_angles.update(extra_angles)

    # Normalize all angles to 0-360
    rotation_angles = {a % 360 for a in rotation_angles}

    # Calculate boundary centroid once
    boundary_centroid = user_boundary.centroid

    # Try each rotation
    for angle in sorted(rotation_angles):
        # Rotate around drainfield's centroid
        rotated = rotate(drainfield_polygon, angle, origin='centroid')

        # Translate to center on boundary
        dx = boundary_centroid.x - rotated.centroid.x
        dy = boundary_centroid.y - rotated.centroid.y
        positioned = translate(rotated, xoff=dx, yoff=dy)

        if polygon_fits(positioned, user_boundary):
            return (True, angle, positioned)

    return (False, 0, drainfield_polygon)


def try_rotations(drainfield_polygon, user_boundary, rotation_step=5):
    """
    FALLBACK: Try rotating every N degrees (used if edge alignment fails)

    Args:
        drainfield_polygon: Shapely Polygon of drainfield
        user_boundary: Shapely Polygon of user boundary
        rotation_step: Degrees between rotation attempts (default 5)

    Returns:
        Tuple of (fits: bool, rotation_angle: float, rotated_polygon: Polygon)
    """
    # First try edge-aligned rotations (smarter approach)
    fits, angle, positioned = try_edge_aligned_rotations(drainfield_polygon, user_boundary)
    if fits:
        return (fits, angle, positioned)

    # Calculate boundary centroid once
    boundary_centroid = user_boundary.centroid

    # Fallback: try every 5 degrees
    for angle in range(0, 360, rotation_step):
        # Rotate around drainfield's centroid
        rotated = rotate(drainfield_polygon, angle, origin='centroid')

        # Translate to center on boundary
        dx = boundary_centroid.x - rotated.centroid.x
        dy = boundary_centroid.y - rotated.centroid.y
        positioned = translate(rotated, xoff=dx, yoff=dy)

        if polygon_fits(positioned, user_boundary):
            return (True, angle, positioned)

    return (False, 0, drainfield_polygon)


def calculate_centered_offset(drainfield_polygon, user_boundary):
    """
    Calculate offset to center the drainfield in the boundary
    
    Args:
        drainfield_polygon: Shapely Polygon of drainfield
        user_boundary: Shapely Polygon of user boundary
        
    Returns:
        Tuple of (dx, dy) offset values
    """
    df_centroid = drainfield_polygon.centroid
    boundary_centroid = user_boundary.centroid
    
    dx = boundary_centroid.x - df_centroid.x
    dy = boundary_centroid.y - df_centroid.y
    
    return (dx, dy)


def calculate_optimal_offset(drainfield_polygon, user_boundary):
    """
    Calculate optimal offset to position drainfield within boundary
    Tries to keep it away from edges while staying centered
    
    Args:
        drainfield_polygon: Shapely Polygon of drainfield (already rotated)
        user_boundary: Shapely Polygon of user boundary
        
    Returns:
        Tuple of (dx, dy) offset values
    """
    # Start with centered position
    dx, dy = calculate_centered_offset(drainfield_polygon, user_boundary)
    
    # Translate to center
    positioned = translate(drainfield_polygon, xoff=dx, yoff=dy)
    
    # Check if it fits at centered position
    if polygon_fits(positioned, user_boundary):
        return (dx, dy)
    
    # If centered doesn't fit, try small adjustments
    # This shouldn't happen if rotation was correct, but safety check
    for offset_x in range(-5, 6):
        for offset_y in range(-5, 6):
            test_dx = dx + offset_x * 0.5
            test_dy = dy + offset_y * 0.5
            test_positioned = translate(drainfield_polygon, xoff=test_dx, yoff=test_dy)
            
            if polygon_fits(test_positioned, user_boundary):
                return (test_dx, test_dy)
    
    # Fallback to centered even if slightly outside
    return (dx, dy)


def calculate_centroid_offset(drainfield_polygon, user_boundary):
    """
    Alias for calculate_optimal_offset (for backward compatibility)
    """
    return calculate_optimal_offset(drainfield_polygon, user_boundary)


def translate_polygon(polygon, dx, dy):
    """
    Translate a polygon by given offsets
    
    Args:
        polygon: Shapely Polygon
        dx: X offset
        dy: Y offset
        
    Returns:
        Translated Shapely Polygon
    """
    return translate(polygon, xoff=dx, yoff=dy)


def get_polygon_bounds(polygon):
    """
    Get bounding box of a polygon
    
    Args:
        polygon: Shapely Polygon
        
    Returns:
        Tuple of (minx, miny, maxx, maxy)
    """
    return polygon.bounds


def polygon_area(polygon):
    """
    Calculate area of a polygon
    
    Args:
        polygon: Shapely Polygon
        
    Returns:
        Area in square feet
    """
    return polygon.area


def validate_boundary(polygon):
    """
    Validate that a boundary polygon is usable
    
    Args:
        polygon: Shapely Polygon
        
    Returns:
        Tuple of (is_valid: bool, error_message: str or None)
    """
    if not polygon.is_valid:
        return (False, "Boundary polygon is not valid (self-intersecting or malformed)")
    
    if polygon.area < 1.0:
        return (False, "Boundary area is too small (< 1 sq ft)")
    
    return (True, None)
