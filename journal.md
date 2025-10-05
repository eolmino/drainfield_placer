# Development Journal - Drainfield Placer

## 2025-10-05 - Critical Bug Fix: Position-Dependent Fit Failure

**Time:** 14:30 UTC
**Status:** ✓ RESOLVED
**Severity:** HIGH

---

### Problem Report

User reported that `simple_test.py` exhibited inconsistent behavior when processing geometrically identical boundaries:

- **Boundary 1** (`test_boundary (script found fit).json`): ✓ Found fit successfully
- **Boundary 2** (`test_boundary (script didn't find fit).json`): ✗ Failed to find fit

Both boundaries had:
- Identical perimeter: 122.51 ft
- Identical area: 804.5 sq ft
- Identical edge lengths and interior angles
- Same shape, just translated to different coordinate positions

---

### Investigation Process

#### Step 1: Geometric Analysis
Compared both boundary files to verify they were truly identical:

**Boundary 1 Position:**
- X range: [-5.14, 13.44]
- Y range: [-0.97, 44.71]
- Centroid: (4.15, 21.87)

**Boundary 2 Position:**
- X range: [26.14, 44.72]
- Y range: [-7.93, 37.76]
- Centroid: (35.43, 14.92)

**Findings:**
- Edge lengths: All identical within 0.000001 ft
- Interior angles: All identical within 0.0001°
- Bounding box dimensions: Identical (18.58 × 45.69 ft)
- **Conclusion:** Boundaries are geometrically identical, just translated ~31 ft in X-direction

#### Step 2: Configuration Analysis
Examined drainfield configuration coordinate system:

**MPS9 Trench Patterns:**
- Pattern [1]: X range [-4.00, 6.00], Y range [0.00, 18.00], Centroid (1.00, 9.00)
- Pattern [2]: X range [-4.00, 6.00], Y range [0.00, 28.00], Centroid (1.00, 14.00)
- All patterns positioned near origin with consistent X range

#### Step 3: Code Review
Analyzed the placement algorithm flow:

1. `selector.py:_try_product()` - Extracts shoulder polygon from config
2. `geometry.py:try_rotations()` - Attempts to find a fit with rotation
3. `geometry.py:try_edge_aligned_rotations()` - Tests rotations aligned to boundary edges
4. `geometry.py:polygon_fits()` - Checks if drainfield is within boundary

#### Step 4: Root Cause Identification

**Critical Bug Found in `geometry.py`:**

The rotation functions (`try_rotations()` and `try_edge_aligned_rotations()`) were:
1. ✓ Rotating the drainfield polygon around its centroid
2. ✗ **NOT translating it to the boundary location**
3. ✓ Checking if it fits within the boundary
4. ✗ Returning the rotated but untranslated polygon

**Why this caused position-dependent behavior:**

```
Drainfield configs positioned at: X ∈ [-4, 6]

Boundary 1 at X ∈ [-5, 13]:
  - Overlaps with drainfield position
  - Rotated drainfield COULD be within boundary
  - Result: ✓ Works (by coincidence)

Boundary 2 at X ∈ [26, 44]:
  - Separated by ~30 ft from drainfield position
  - Rotated drainfield NEVER within boundary
  - Result: ✗ Fails
```

The algorithm was effectively checking: "Does the drainfield fit at ITS CURRENT POSITION?" instead of "Does the drainfield fit ANYWHERE in the boundary?"

---

### Solution Implemented

#### Modified Files

**1. `geometry.py:try_edge_aligned_rotations()` (lines 130-185)**

**Before:**
```python
for angle in sorted(rotation_angles):
    rotated = rotate(drainfield_polygon, angle, origin='centroid')

    if polygon_fits(rotated, user_boundary):
        return (True, angle, rotated)
```

**After:**
```python
# Calculate boundary centroid once
boundary_centroid = user_boundary.centroid

for angle in sorted(rotation_angles):
    # Rotate around drainfield's centroid
    rotated = rotate(drainfield_polygon, angle, origin='centroid')

    # Translate to center on boundary
    dx = boundary_centroid.x - rotated.centroid.x
    dy = boundary_centroid.y - rotated.centroid.y
    positioned = translate(rotated, xoff=dx, yoff=dy)

    if polygon_fits(positioned, user_boundary):
        return (True, angle, positioned)
```

**2. `geometry.py:try_rotations()` (lines 188-221)**

Applied same fix to the fallback rotation loop:
- Added boundary centroid calculation
- Added translation step after each rotation
- Check fit on positioned polygon instead of just rotated polygon

**3. `selector.py:_try_product()` (lines 129-148)**

Updated offset calculation logic:

**Before:**
```python
if fits:
    dx, dy = calculate_centroid_offset(fitted_polygon, user_boundary)
```

**After:**
```python
if fits:
    # fitted_polygon is already positioned, calculate offset from original
    boundary_centroid = user_boundary.centroid
    original_centroid = shoulder_polygon.centroid
    dx = boundary_centroid.x - original_centroid.x
    dy = boundary_centroid.y - original_centroid.y
```

The offset now correctly represents the translation from the original config position to the boundary centroid, which is what `placer.py` expects.

---

### Testing & Verification

Created `test_fix_simple.py` to verify the fix with both boundary files.

**Test Configuration:**
- Required sqft: 100
- Config type: TRENCH
- Product priority: MPS9 → ARC24 → EQ36LP

**Results:**

```
Boundary 1 (previously worked):
  Status: PASS ✓
  Product: MPS9
  Pattern: [2, 2]
  Credit: 120.0 sq ft
  Rotation: 0.0°

Boundary 2 (previously failed):
  Status: PASS ✓
  Product: MPS9
  Pattern: [2, 2]
  Credit: 120.0 sq ft
  Rotation: 0.0°
```

**Conclusion:** Both boundaries now find identical configurations, confirming the fix is working correctly.

---

### Technical Impact

**Before Fix:**
- Algorithm was position-dependent
- Only worked if user boundary happened to overlap with drainfield config coordinates
- Unpredictable failures based on where user drew boundary in CAD space

**After Fix:**
- Algorithm is now position-independent
- Works regardless of absolute coordinates
- Drainfield configs are properly translated to boundary location before fit testing
- Consistent behavior across all boundary positions

---

### Lessons Learned

1. **Always test with diverse input data:** The bug only manifested when boundaries were positioned far from the origin
2. **Coordinate system assumptions:** Never assume geometric objects will be at specific absolute positions
3. **Transform order matters:** Rotation must be followed by translation to properly position objects
4. **Test position-independence:** For geometric algorithms, test with identical shapes at different positions

---

### Future Recommendations

1. Add unit tests that verify position-independence by testing identical shapes at different coordinates
2. Consider normalizing all input boundaries to a standard position before processing
3. Add validation that checks for coordinate system assumptions in geometric algorithms
4. Document the expected coordinate system for all geometric operations

---

**Issue Closed:** 2025-10-05 15:00 UTC
**Verified By:** User acceptance testing with production boundary files
**Git Commit:** (pending)
