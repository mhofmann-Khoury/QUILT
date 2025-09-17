# Quilt

A knit-programming library for modular combination of knitted structures defined by the knitout machine knitting language.

[![Build Status](https://img.shields.io/github/workflow/status/mhofmann-Khoury/QUILT/CI)](https://github.com/mhofmann-Khoury/QUILT/actions)
[![PyPI Version](https://img.shields.io/pypi/v/quilt-knit)](https://pypi.org/project/quilt-knit/)
[![Python Versions](https://img.shields.io/pypi/pyversions/quilt-knit)](https://pypi.org/project/quilt-knit/)

## Overview

Quilt enables you to combine individual knitted swatches into larger, more complex structures through:

- **Course-wise merging** (horizontal combination)
- **Wale-wise merging** (vertical combination)
- **Quilt construction** (complex grid patterns)

Mix and match different stitch patterns including jersey, rib, seed, lace, cable, and jacquard.

## Quick Install

```bash
pip install quilt-knit
```

Requires Python 3.11 or higher.

## Documentation

**📖 Full documentation is available at: https://mhofmann-Khoury.github.io/quilt-knit/**

The documentation includes:
- Complete installation instructions
- Detailed usage examples
- API reference
- Advanced quilt patterns

## Quick Example

```python
"""Example of left->right course merge"""
from quilt_knit.swatch.Swatch import Swatch
from quilt_knit.swatch.course_wise_merging.Course_Wise_Connection import Course_Wise_Connection
from quilt_knit.swatch.course_wise_merging.Course_Merge_Process import Course_Merge_Process

# Create and merge two swatches horizontally
left_swatch = Swatch("left", "left_program.k")
right_swatch = Swatch("right", "right_program.k")

connection = Course_Wise_Connection(left_swatch, right_swatch)
merger = Course_Merge_Process(connection)
merger.merge_swatches()
merger.compile_to_dat('merged_output')
```

## License

This project is licensed for non-commercial use. See the [LICENSE](LICENSE.md) file for details.
