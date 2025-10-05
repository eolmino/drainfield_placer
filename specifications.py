"""
Specifications Generator Module
Generates formatted septic system specification text blocks for CAD drawings
"""

import csv
from pathlib import Path


class SpecificationGenerator:
    """Generates formatted specification text blocks"""

    def __init__(self, data_dir="data"):
        """Initialize specification generator"""
        self.data_dir = Path(data_dir)
        self.available_tank_sizes = self._load_available_tank_sizes()
        self.available_dosing_tank_sizes = self._load_available_dosing_tank_sizes()

    def _load_available_tank_sizes(self):
        """Load available septic tank sizes from fdep_tanks.csv"""
        csv_path = self.data_dir / "fdep_tanks.csv"

        if not csv_path.exists():
            # Return common sizes as fallback
            return [750, 900, 1000, 1050, 1200, 1250, 1500]

        sizes = set()
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('tank_type') == 'septic' and row.get('effective_gallons'):
                    try:
                        sizes.add(int(row['effective_gallons']))
                    except (ValueError, TypeError):
                        pass

        return sorted(sizes) if sizes else [750, 900, 1000, 1050, 1200, 1250, 1500]

    def _load_available_dosing_tank_sizes(self):
        """Load available dosing tank sizes - limited to 300 and 500 gallon tanks only"""
        # Contractors typically use only 300 or 500 gallon dosing tanks
        return [300, 500]

    def get_actual_tank_size(self, required_gallons):
        """
        Get the actual available tank size that meets or exceeds the requirement

        Args:
            required_gallons: Minimum required tank capacity

        Returns:
            Next available tank size that meets requirement
        """
        for size in self.available_tank_sizes:
            if size >= required_gallons:
                return size

        # If no exact match, return the required size
        return required_gallons

    def get_actual_dosing_tank_size(self, required_gallons):
        """
        Get the actual available dosing tank size that meets or exceeds the requirement
        Uses 300 or 500 gallon dosing tanks. For larger requirements, uses septic tank sizes.

        Args:
            required_gallons: Minimum required dosing tank capacity

        Returns:
            Next available tank size that meets requirement
        """
        # Try dosing tank sizes first (300 or 500)
        for size in self.available_dosing_tank_sizes:
            if size >= required_gallons:
                return size

        # If requirement > 500, use single compartment septic tank instead
        for size in self.available_tank_sizes:
            if size >= required_gallons:
                return size

        # Fallback
        return required_gallons

    def generate_specification(self,
                              flow_gpd,
                              config_type,
                              drainfield_size_required,
                              unobstructed_area_required,
                              tank_size_required=None,
                              atu_size_required=None,
                              dosing_tank_required=None,
                              num_homes=1,
                              is_split=False,
                              benchmark_text=None,
                              core_depth=None,
                              core_above_below=None,
                              title_suffix=None,
                              atu_manufacturer=None,
                              drainfield_size_actual=None,
                              boundary_area_actual=None):
        """
        Generate formatted specification text block

        Args:
            flow_gpd: Sewage flow in gallons per day
            config_type: 'trench', 'bed', 'trench_atu', 'bed_atu', etc.
            drainfield_size_required: Required drainfield square footage
            unobstructed_area_required: Required unobstructed area square footage
            tank_size_required: Required septic tank capacity (if not ATU)
            atu_size_required: Required ATU capacity (if ATU system)
            dosing_tank_required: Required dosing tank capacity (residential)
            num_homes: Number of dwelling units
            is_split: True if split drainfield system
            benchmark_text: Optional benchmark description
            core_depth: Optional core depth value
            core_above_below: Optional 'ABOVE' or 'BELOW' for core
            title_suffix: Optional suffix for title (e.g., "Barn")
            atu_manufacturer: Optional ATU manufacturer name
            drainfield_size_actual: Actual drainfield size chosen (credit sqft)
            boundary_area_actual: Actual boundary area from CAD file

        Returns:
            Formatted specification text block as string
        """
        lines = []

        # Get actual values
        actual_drainfield = drainfield_size_actual if drainfield_size_actual is not None else drainfield_size_required
        actual_boundary = int(boundary_area_actual) if boundary_area_actual is not None else unobstructed_area_required

        # Tank or ATU information
        has_atu = 'atu' in config_type.lower()
        actual_tank_size = None
        actual_dosing_tank_size = None

        if not has_atu and tank_size_required:
            actual_tank_size = self.get_actual_tank_size(tank_size_required)

        if dosing_tank_required:
            actual_dosing_tank_size = self.get_actual_dosing_tank_size(dosing_tank_required)

        # Build lines in REVERSE ORDER (bottom to top as displayed)

        # Core information (bottom lines)
        if core_depth is not None and core_above_below:
            lines.append(f"CORE #2: {core_depth:.2f} feet {core_above_below} B.M.")
            lines.append(f"CORE #1: {core_depth:.2f} feet {core_above_below} B.M.")
        else:
            lines.append("CORE #2:")
            lines.append("CORE #1:")

        # Unobstructed area
        if is_split:
            lines.append(f"{actual_boundary} SF OF UNOBSTRUCTED AREA REQUIRED FOR DRAINFIELD #2, {unobstructed_area_required} SF REQUIRED.")
            lines.append(f"{actual_boundary} SF OF UNOBSTRUCTED AREA REQUIRED FOR DRAINFIELD #1, {unobstructed_area_required} SF REQUIRED.")
        else:
            lines.append(f"{actual_boundary} SF OF UNOBSTRUCTED AREA REQUIRED, {unobstructed_area_required} SF REQUIRED.")

        # Configuration type
        config_name = self._format_config_name(config_type)
        lines.append(f"DRAINFIELD CONFIGURATION: {config_name}")

        # Drainfield information
        if is_split:
            # Split drainfield
            lines.append(f"PROPOSED {int(actual_drainfield)} SF DRAINFIELD #2, {drainfield_size_required} SF REQUIRED.")
            lines.append(f"PROPOSED {int(actual_drainfield)} SF DRAINFIELD #1, {drainfield_size_required} SF REQUIRED.")
        else:
            # Single drainfield
            if has_atu:
                lines.append(f"PROPOSED {int(actual_drainfield)} SF DRAINFIELD, {drainfield_size_required} SF REQUIRED WITH 25% REDUCTION.")
            else:
                lines.append(f"PROPOSED {int(actual_drainfield)} SF DRAINFIELD, {drainfield_size_required} SF REQUIRED.")

        # Tank or ATU information
        if has_atu and atu_size_required:
            # ATU system
            lines.append(f"{atu_size_required} GALLON AEROBIC TREATMENT UNIT REQUIRED.")
            if atu_manufacturer:
                lines.append(f"PROPOSED {atu_manufacturer} {flow_gpd} GPD ATU")
        elif tank_size_required:
            # Septic tank system
            if num_homes > 1:
                additional_gallons = num_homes * 75
                lines.append(f"AN ADDITIONAL {additional_gallons} GALLONS APPLIED TO THE SEPTIC TANK FOR {num_homes} DWELLING UNITS")
            # Add dosing tank line (appears after septic tank in output)
            if actual_dosing_tank_size:
                lines.append(f"PROPOSED {actual_dosing_tank_size} GALLON DOSING TANK, {dosing_tank_required} GALLON REQUIRED.")
            # Add septic tank line
            lines.append(f"PROPOSED {actual_tank_size} GALLON SEPTIC TANK, {tank_size_required} GALLON REQUIRED.")

        # Benchmark
        if benchmark_text:
            lines.append(f"BENCHMARK: {benchmark_text}")
        else:
            lines.append("BENCHMARK:")

        # Title (top lines)
        if title_suffix:
            lines.append("=" * 50)
            lines.append(f"SEPTIC SYSTEM SPECIFICATIONS ({title_suffix})")
            lines.append("=" * 50)
        else:
            lines.append("=" * 30)
            lines.append("SEPTIC SYSTEM SPECIFICATIONS")
            lines.append("=" * 30)

        return "\n".join(lines)

    def _format_config_name(self, config_type):
        """
        Format configuration type for display

        Args:
            config_type: Configuration type string

        Returns:
            Formatted configuration name
        """
        if 'trench' in config_type.lower():
            return 'Trench'
        elif 'bed' in config_type.lower():
            return 'Bed'
        else:
            return config_type.capitalize()

    def generate_from_result(self, result, tank_info, benchmark_text=None,
                           core_depth=None, core_above_below=None,
                           title_suffix=None, num_homes=1, boundary_area=None):
        """
        Generate specification from drainfield placement result

        Args:
            result: Drainfield placement result dictionary
            tank_info: Tank sizing information dictionary
            benchmark_text: Optional benchmark description
            core_depth: Optional core depth value
            core_above_below: Optional 'ABOVE' or 'BELOW'
            title_suffix: Optional title suffix
            num_homes: Number of dwelling units
            boundary_area: Actual boundary area from CAD file

        Returns:
            Formatted specification text block as string
        """
        # Extract information from result
        flow_gpd = result.get('flow_gpd', 0)
        config_type = result.get('config_type', 'trench')
        is_split = result.get('is_split', False)
        drainfield_size_required = result.get('drainfield_size_required', 0)

        # Get drainfield size and unobstructed area
        if is_split:
            # For split systems, get from one of the drainfields
            df1_metadata = result['drainfield_1']['metadata']
            drainfield_size_actual = df1_metadata['credit_sqft']
            unobstructed_area_required = df1_metadata.get('unobstructed_area', 0)
        else:
            metadata = result.get('metadata', {})
            drainfield_size_actual = metadata.get('credit_sqft', 0)
            unobstructed_area_required = metadata.get('unobstructed_area', 0)

        # Use boundary_area if provided, otherwise use result's boundary_area
        boundary_area_actual = boundary_area if boundary_area is not None else result.get('boundary_area')

        # Tank or ATU size
        has_atu = 'atu' in config_type.lower()
        tank_size = None
        atu_size = None

        if has_atu:
            atu_size = tank_info.get('atu_size')
        else:
            tank_size = tank_info.get('septic_tank')

        return self.generate_specification(
            flow_gpd=flow_gpd,
            config_type=config_type,
            drainfield_size_required=drainfield_size_required,
            unobstructed_area_required=unobstructed_area_required,
            tank_size_required=tank_size,
            atu_size_required=atu_size,
            num_homes=num_homes,
            is_split=is_split,
            benchmark_text=benchmark_text,
            core_depth=core_depth,
            core_above_below=core_above_below,
            title_suffix=title_suffix,
            drainfield_size_actual=drainfield_size_actual,
            boundary_area_actual=boundary_area_actual
        )


# Convenience function
def generate_specification_text(**kwargs):
    """
    Quick function to generate specification text

    Args:
        **kwargs: All arguments for generate_specification

    Returns:
        Formatted specification text block
    """
    generator = SpecificationGenerator()
    return generator.generate_specification(**kwargs)
