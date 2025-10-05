"""
Drainfield Placer - Main Application Entry Point
Simple console interface for quick testing
"""

import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from drainfield_placer import (
    ConfigLoader,
    DrainFieldSelector,
    parse_user_boundary,
    validate_boundary,
    place_drainfield,
    place_split_drainfield,
    create_placement_summary
)


class DrainFieldPlacer:
    """Main application class"""
    
    def __init__(self, json_dir=r"C:\drainfield_generator\json"):
        """Initialize the application"""
        print("=" * 60)
        print("  DRAINFIELD PLACER - Automatic Configuration Tool")
        print("=" * 60)
        print()
        
        self.config_loader = ConfigLoader(json_dir)
        self.selector = DrainFieldSelector(self.config_loader)
        
        # Load all configurations at startup
        if not self.config_loader.load_all_configs():
            print("\n⚠ Warning: Not all configuration files loaded!")
        print()
    
    def run_simple_test(self, required_sqft, boundary_width, boundary_height):
        """
        Run a simple test with a rectangular boundary
        
        Args:
            required_sqft: Required square footage
            boundary_width: Width of rectangular boundary
            boundary_height: Height of rectangular boundary
        """
        print(f"TEST SCENARIO")
        print(f"  Required: {required_sqft} sq ft")
        print(f"  Boundary: {boundary_width} ft × {boundary_height} ft")
        print()
        
        # Create a simple rectangular boundary
        from shapely.geometry import Polygon
        user_boundary = Polygon([
            (0, 0),
            (boundary_width, 0),
            (boundary_width, boundary_height),
            (0, boundary_height)
        ])
        
        # Validate boundary
        is_valid, error = validate_boundary(user_boundary)
        if not is_valid:
            print(f"❌ Boundary Error: {error}")
            return None
        
        print("✓ Boundary validated")
        print()
        
        # Try standard trench first
        print("Attempting selection...")
        result = self.selector.select_configuration(
            user_boundary,
            required_sqft,
            'trench'
        )
        
        # Display results
        summary = create_placement_summary(result)
        self.print_summary(summary)
        
        return result
    
    def run_hierarchy_test(self, flow_gpd, boundary_width, boundary_height):
        """
        Run a full hierarchy test
        
        Args:
            flow_gpd: Gallons per day
            boundary_width: Width of rectangular boundary
            boundary_height: Height of rectangular boundary
        """
        print(f"FULL HIERARCHY TEST")
        print(f"  Flow: {flow_gpd} GPD")
        print(f"  Boundary: {boundary_width} ft × {boundary_height} ft")
        print()
        
        # Create a simple rectangular boundary
        from shapely.geometry import Polygon
        user_boundary = Polygon([
            (0, 0),
            (boundary_width, 0),
            (boundary_width, boundary_height),
            (0, boundary_height)
        ])
        
        # Apply full hierarchy
        print("Applying selection hierarchy...")
        result = self.selector.apply_hierarchy(user_boundary, flow_gpd)
        
        # Display results
        summary = create_placement_summary(result)
        self.print_summary(summary)
        
        return result
    
    def print_summary(self, summary):
        """Print formatted summary"""
        print()
        print("=" * 60)
        print(f"STATUS: {summary['status']}")
        print("=" * 60)
        
        if summary['status'].startswith('SUCCESS'):
            if 'SPLIT' in summary['status']:
                # Split system
                print(f"\nConfiguration: {summary['config_type']}")
                print(f"Flow: {summary['flow_gpd']} GPD")
                print(f"Required per field: {summary['required_sqft_each']} sq ft")
                print()
                
                print("DRAINFIELD 1:")
                df1 = summary['drainfield_1']
                print(f"  Product: {df1['product']}")
                print(f"  Pattern: {df1['pattern']}")
                print(f"  Pieces: {df1['num_pieces']}")
                print(f"  Credit: {df1['credit_sqft']} sq ft")
                print(f"  Rotation: {df1['rotation']}°")
                print()
                
                print("DRAINFIELD 2:")
                df2 = summary['drainfield_2']
                print(f"  Product: {df2['product']}")
                print(f"  Pattern: {df2['pattern']}")
                print(f"  Pieces: {df2['num_pieces']}")
                print(f"  Credit: {df2['credit_sqft']} sq ft")
                print(f"  Rotation: {df2['rotation']}°")
            else:
                # Single drainfield
                print(f"\nProduct: {summary['product']}")
                print(f"Configuration: {summary['config_type']}")
                print(f"Pattern: {summary['pattern']}")
                print(f"Pieces: {summary['num_pieces']}")
                print(f"Credit: {summary['credit_sqft']} sq ft")
                print(f"Rectangular: {summary['is_rectangular']}")
                print(f"Rotation: {summary['rotation']}°")
                print(f"Offset: ({summary['offset_x']}, {summary['offset_y']})")
                
                if summary.get('flow_gpd') != 'N/A':
                    print(f"\nFlow: {summary['flow_gpd']} GPD")
                    print(f"Required: {summary['required_sqft']} sq ft")
        else:
            # Failed
            print(f"\nReason: {summary['reason']}")
            print(f"Message: {summary['message']}")
            print(f"\nConfigurations attempted:")
            for config in summary['attempted']:
                print(f"  - {config}")
        
        print()


def main():
    """Main entry point"""
    # Create application instance
    app = DrainFieldPlacer()
    
    # Simple console prompt
    print("Quick Test Mode")
    print("-" * 60)
    
    try:
        required_sqft = float(input("Enter required square footage: "))
        boundary_width = float(input("Enter boundary width (ft): "))
        boundary_height = float(input("Enter boundary height (ft): "))
        
        print()
        result = app.run_simple_test(required_sqft, boundary_width, boundary_height)
        
    except ValueError:
        print("\n❌ Invalid input. Please enter numeric values.")
        return
    except KeyboardInterrupt:
        print("\n\nExiting...")
        return


if __name__ == "__main__":
    main()
