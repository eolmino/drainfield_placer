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

# Import new modules for full design mode
from sewage_flow import SewageFlowCalculator
from tank_sizing import TankSizer
from specifications import SpecificationGenerator
from database import SepticDatabase
from drainfield_requirements import DrainFieldRequirements


class DrainFieldPlacer:
    """Main application class"""
    
    def __init__(self, json_dir="json", data_dir="data"):
        """Initialize the application"""
        print("=" * 60)
        print("  DRAINFIELD PLACER - Automatic Configuration Tool")
        print("=" * 60)
        print()

        self.config_loader = ConfigLoader(json_dir)
        self.selector = DrainFieldSelector(self.config_loader)

        # Initialize new modules for full design mode
        self.flow_calculator = SewageFlowCalculator(data_dir)
        self.tank_sizer = TankSizer(data_dir)
        self.spec_generator = SpecificationGenerator()
        self.drainfield_requirements = DrainFieldRequirements(data_dir)

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

    def run_full_design(self, bedrooms, square_footage, water_type, net_acreage,
                       boundary_polygon, boundary_json=None, property_id=None,
                       benchmark_text=None, num_homes=1, update_database=True):
        """
        Run full design workflow from building specs to drainfield placement

        Args:
            bedrooms: Number of bedrooms
            square_footage: Building square footage
            water_type: 'w' for well, 'p' for public
            net_acreage: Net acreage of property
            boundary_polygon: Shapely Polygon of user-drawn boundary
            boundary_json: Optional original CAD JSON with boundary (for output)
            property_id: Optional property ID for database update
            benchmark_text: Optional benchmark description
            num_homes: Number of dwelling units (default 1)
            update_database: Whether to update database (default True)

        Returns:
            Dictionary with complete design results
        """
        print(f"FULL DESIGN MODE")
        print(f"  Bedrooms: {bedrooms}")
        print(f"  Square Footage: {square_footage}")
        print(f"  Water Type: {'Well' if water_type == 'w' else 'Public'}")
        print(f"  Net Acreage: {net_acreage}")
        if num_homes > 1:
            print(f"  Dwelling Units: {num_homes}")
        print()

        # Step 1: Calculate sewage flow
        print("Step 1: Calculating sewage flow...")
        flow_gpd = self.flow_calculator.calculate_flow(bedrooms, square_footage)
        print(f"  Sewage Flow: {flow_gpd} GPD")
        print()

        # Step 2: Determine tank requirements
        print("Step 2: Determining tank requirements...")
        septic_tank_size = self.tank_sizer.get_septic_tank_size(flow_gpd, num_homes)
        dosing_tank_size = self.tank_sizer.get_pump_tank_size(flow_gpd, is_residential=True)
        atu_size = self.tank_sizer.calculate_atu_size(bedrooms, square_footage, flow_gpd)
        print(f"  Septic Tank Required: {septic_tank_size} gallons")
        print(f"  Dosing Tank Required: {dosing_tank_size} gallons")
        if atu_size:
            print(f"  ATU Size (if used): {atu_size} gallons")
        print()

        # Step 3: Apply hierarchy to find drainfield configuration
        print("Step 3: Applying configuration hierarchy...")
        result = self.selector.apply_hierarchy(boundary_polygon, flow_gpd)

        if not result['success']:
            print(f"  ❌ Failed: {result.get('reason', 'Unknown')}")
            print(f"  {result.get('message', '')}")
            return result

        # Step 4: Calculate areas
        boundary_area = int(boundary_polygon.area)
        config_type = result['config_type']
        is_split = result.get('is_split', False)

        # Get unobstructed area required from requirements table
        requirements = self.drainfield_requirements.get_requirements(flow_gpd, config_type)
        if requirements:
            drainfield_size_required = requirements['drainfield_size']
            unobstructed_area_required = requirements['unobstructed_area']
        else:
            # Fallback to metadata if requirements not found
            if is_split:
                df1_metadata = result['drainfield_1']['metadata']
                drainfield_size_required = df1_metadata.get('credit_sqft', 0)
                unobstructed_area_required = df1_metadata.get('unobstructed_area', 0)
            else:
                metadata = result.get('metadata', {})
                drainfield_size_required = metadata.get('credit_sqft', 0)
                unobstructed_area_required = metadata.get('unobstructed_area', 0)

        # Step 5: Prepare database fields
        gpd_multiplier = 1500 if water_type == 'w' else 2500
        authorized_flow = int(net_acreage * gpd_multiplier)

        # Determine rate and config booleans
        is_bed = 'bed' in config_type.lower()
        is_trench = 'trench' in config_type.lower()
        rate = '0.6/Sand' if is_bed else '0.8/Sand'

        # Step 6: Get benchmark and core data from database (if property_id provided)
        core_depth = None
        core_above_below = None

        if property_id and update_database:
            try:
                db = SepticDatabase()
                if db.connect():
                    db_data = db.get_benchmark_and_core_data(property_id)
                    if db_data:
                        if not benchmark_text:
                            benchmark_text = db_data.get('benchmark_text')
                        core_depth = db_data.get('core_depth')
                        core_above_below = db_data.get('core_above_below')
                    db.disconnect()
            except Exception as e:
                print(f"  Note: Could not retrieve database info: {e}")

        # Step 7: Generate specification text
        print("Step 4: Generating specifications...")
        has_atu = 'atu' in config_type.lower()

        # Get actual drainfield credit from result
        if is_split:
            df1_metadata = result['drainfield_1']['metadata']
            drainfield_size_actual = df1_metadata.get('credit_sqft', drainfield_size_required)
        else:
            metadata = result.get('metadata', {})
            drainfield_size_actual = metadata.get('credit_sqft', drainfield_size_required)

        spec_text = self.spec_generator.generate_specification(
            flow_gpd=flow_gpd,
            config_type=config_type,
            drainfield_size_required=drainfield_size_required,
            unobstructed_area_required=unobstructed_area_required,
            tank_size_required=septic_tank_size if not has_atu else None,
            atu_size_required=atu_size if has_atu else None,
            dosing_tank_required=dosing_tank_size if not has_atu else None,
            num_homes=num_homes,
            is_split=is_split,
            benchmark_text=benchmark_text,
            core_depth=core_depth,
            core_above_below=core_above_below,
            drainfield_size_actual=drainfield_size_actual,
            boundary_area_actual=boundary_area
        )

        # Step 8: Update database
        if property_id and update_database:
            print("Step 5: Updating database...")
            try:
                db = SepticDatabase()
                if db.connect():
                    success = db.update_septic_system_record(
                        property_id=property_id,
                        net_acreage=net_acreage,
                        flow_gpd=flow_gpd,
                        authorized_flow=authorized_flow,
                        gpd_multiplier=gpd_multiplier,
                        unobstructed_area_available=boundary_area,
                        unobstructed_area_required=unobstructed_area_required,
                        benchmark_text=benchmark_text,
                        rate=rate,
                        is_trench=is_trench,
                        is_bed=is_bed
                    )
                    db.disconnect()

                    if success:
                        print(f"  ✓ Database updated for property {property_id}")
                    else:
                        print(f"  ⚠ Database update failed")
            except Exception as e:
                print(f"  ⚠ Database error: {e}")
        print()

        # Add specification text to result
        result['specification_text'] = spec_text
        result['flow_gpd'] = flow_gpd
        result['tank_size'] = septic_tank_size
        result['atu_size'] = atu_size
        result['boundary_area'] = boundary_area
        result['drainfield_size_required'] = drainfield_size_required
        result['unobstructed_area_required'] = unobstructed_area_required

        # Step 6: Generate output JSON with placed drainfield
        if boundary_json:
            print("Step 6: Generating output JSON with placed drainfield...")
            try:
                # Get actual tank sizes (from spec generator logic)
                actual_septic_tank = None
                actual_dosing_tank = None

                if not has_atu:
                    actual_septic_tank = self.spec_generator.get_actual_tank_size(septic_tank_size)
                    actual_dosing_tank = self.spec_generator.get_actual_dosing_tank_size(dosing_tank_size)

                # Place drainfield into the CAD JSON
                if is_split:
                    output_json = place_split_drainfield(boundary_json, result, spec_text,
                                                        actual_septic_tank, actual_dosing_tank)
                else:
                    output_json = place_drainfield(boundary_json, result, spec_text,
                                                  actual_septic_tank, actual_dosing_tank)

                # Save to output file
                output_filename = f"output_drainfield_{property_id if property_id else 'design'}.json"
                with open(output_filename, 'w') as f:
                    json.dump(output_json, f, indent=2)

                print(f"  ✓ Output saved to: {output_filename}")
                result['output_json_file'] = output_filename
            except Exception as e:
                print(f"  ⚠ Error creating output JSON: {e}")
        print()

        # Display summary
        summary = create_placement_summary(result)
        self.print_summary(summary)

        # Display specification text
        print()
        print("SPECIFICATION TEXT:")
        print("-" * 60)
        print(spec_text)
        print("-" * 60)
        print()

        return result


def main():
    """Main entry point"""
    # Create application instance
    app = DrainFieldPlacer()

    # Mode selection
    print("MODE SELECTION")
    print("-" * 60)
    print("1. Quick Test Mode - Enter required sqft directly")
    print("2. Full Design Mode - Enter building specs, calculate everything")
    print()

    try:
        mode = input("Select mode (1 or 2): ").strip()

        if mode == "1":
            # Quick Test Mode (existing)
            print()
            print("Quick Test Mode")
            print("-" * 60)

            required_sqft = float(input("Enter required square footage: "))
            boundary_width = float(input("Enter boundary width (ft): "))
            boundary_height = float(input("Enter boundary height (ft): "))

            print()
            result = app.run_simple_test(required_sqft, boundary_width, boundary_height)

        elif mode == "2":
            # Full Design Mode (new)
            print()
            print("Full Design Mode")
            print("-" * 60)

            # Get building specifications
            bedrooms = int(input("Number of bedrooms: "))
            square_footage = float(input("Building square footage: "))

            # Get water type
            water_type = input("Water type (w=well, p=public): ").strip().lower()
            while water_type not in ['w', 'p']:
                print("Invalid input. Enter 'w' for well or 'p' for public.")
                water_type = input("Water type (w=well, p=public): ").strip().lower()

            # Get net acreage
            net_acreage = float(input("Net acreage: "))

            # Get boundary from JSON file
            boundary_json_path = input("Path to boundary JSON file: ").strip()

            # Load and parse boundary
            try:
                with open(boundary_json_path, 'r') as f:
                    boundary_data = json.load(f)

                boundary_polygon = parse_user_boundary(boundary_data)
                is_valid, error = validate_boundary(boundary_polygon)

                if not is_valid:
                    print(f"\n❌ Boundary Error: {error}")
                    return

                print(f"✓ Boundary loaded and validated")
                print(f"  Area: {boundary_polygon.area:.1f} sq ft")

            except FileNotFoundError:
                print(f"\n❌ File not found: {boundary_json_path}")
                return
            except json.JSONDecodeError:
                print(f"\n❌ Invalid JSON file")
                return
            except Exception as e:
                print(f"\n❌ Error loading boundary: {e}")
                return

            # Property ID
            property_id = input("Property ID (press Enter to skip): ").strip()
            if not property_id:
                property_id = None

            # Benchmark text (optional)
            benchmark_text = input("Benchmark text (press Enter to skip): ").strip()
            if not benchmark_text:
                benchmark_text = None

            # Number of homes (default 1)
            num_homes_input = input("Number of dwelling units (default 1): ").strip()
            num_homes = int(num_homes_input) if num_homes_input else 1

            print()
            result = app.run_full_design(
                bedrooms=bedrooms,
                square_footage=square_footage,
                water_type=water_type,
                net_acreage=net_acreage,
                boundary_polygon=boundary_polygon,
                boundary_json=boundary_data,
                property_id=property_id,
                benchmark_text=benchmark_text,
                num_homes=num_homes,
                update_database=(property_id is not None)
            )

        else:
            print("\n❌ Invalid mode selection. Please enter 1 or 2.")
            return

    except ValueError as e:
        print(f"\n❌ Invalid input: {e}")
        return
    except KeyboardInterrupt:
        print("\n\nExiting...")
        return


if __name__ == "__main__":
    main()
