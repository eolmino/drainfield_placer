"""
DRAINFIELD PLACER - Simple Square Footage Search
Finds first configuration >= required square footage that fits in boundary
"""

import json
from pathlib import Path

from config_loader import ConfigLoader
from selector import DrainFieldSelector
from geometry import parse_user_boundary, validate_boundary
from placer import create_placement_summary, place_drainfield


def main():
    print("=" * 60)
    print("  DRAINFIELD PLACER")
    print("=" * 60)
    print()
    
    # Load configurations
    print("Loading configurations...")
    loader = ConfigLoader(r"C:\drainfield_placer\json")
    if not loader.load_all_configs():
        print("WARNING: Not all config files loaded")
    
    selector = DrainFieldSelector(loader)
    print()
    
    # Load boundary file
    boundary_file = "test_boundary.json"
    
    if not Path(boundary_file).exists():
        print(f"ERROR: {boundary_file} not found")
        input("\nPress Enter to exit...")
        return
    
    print(f"Loading boundary: {boundary_file}")
    with open(boundary_file, 'r') as f:
        cad_json = json.load(f)
    
    # Parse boundary
    try:
        user_boundary = parse_user_boundary(cad_json, 'polyline_boundary')
        print(f"Boundary loaded ({user_boundary.area:.1f} sq ft)")
    except Exception as e:
        print(f"ERROR: {e}")
        input("\nPress Enter to exit...")
        return
    
    # Validate boundary
    is_valid, error = validate_boundary(user_boundary)
    if not is_valid:
        print(f"ERROR: {error}")
        input("\nPress Enter to exit...")
        return
    
    print()
    
    # Get required square footage
    try:
        required_sqft = float(input("Enter required square footage: "))
    except ValueError:
        print("ERROR: Invalid number")
        input("\nPress Enter to exit...")
        return
    
    print()
    print(f"Searching for configuration >= {required_sqft} sq ft...")
    print()
    
    # Try each config type with the SAME square footage requirement
    config_types = [
        ('trench', 'TRENCH'),
        ('bed', 'BED'),
        ('trench_atu', 'TRENCH+ATU'),
        ('bed_atu', 'BED+ATU')
    ]
    
    for config_type, type_name in config_types:
        print(f"Trying {type_name}...", end=' ')
        
        result = selector.select_configuration(
            user_boundary=user_boundary,
            required_sqft=required_sqft,
            config_type=config_type
        )
        
        if result['success']:
            print("FOUND!")
            
            # Display results
            summary = create_placement_summary(result)
            
            print()
            print("=" * 60)
            print("SUCCESS")
            print("=" * 60)
            print()
            print(f"Product:      {summary['product'].upper()}")
            print(f"Type:         {summary['config_type']}")
            print(f"Pattern:      {summary['pattern']}")
            print(f"Pieces:       {summary['num_pieces']}")
            print(f"Credit:       {summary['credit_sqft']} sq ft")
            print(f"Rectangular:  {'Yes' if summary['is_rectangular'] else 'No'}")
            print(f"Rotation:     {summary['rotation']}°")
            print()
            
            # Place drainfield
            print("Placing drainfield...")
            
            try:
                output_cad = place_drainfield(cad_json, result)
                
                output_file = "output_with_drainfield.json"
                with open(output_file, 'w') as f:
                    json.dump(output_cad, f, indent=2)
                
                print(f"Saved to: {output_file}")
                
            except Exception as e:
                print(f"ERROR: {e}")
            
            print()
            input("Press Enter to exit...")
            return
        else:
            print("no fit")
    
    # Nothing fit
    print()
    print("=" * 60)
    print("NO FIT")
    print("=" * 60)
    print()
    print(f"No configuration >= {required_sqft} sq ft fits in boundary")
    print()
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
