# Execution Scripts

This folder contains **deterministic Python scripts** that perform the actual work.

## Purpose

Execution scripts handle:
- API calls
- Data processing
- File operations
- Storage and cloud uploads

## Guidelines

- Scripts should be **fast, testable, and repeatable**
- If something runs more than once, it belongs in code
- Secrets and tokens should be loaded from `.env`
- Keep scripts focused on a single responsibility
- Always handle errors gracefully and return meaningful exit codes

## File Naming

Use descriptive, lowercase names with underscores:
- `scrape_single_site.py`
- `process_csv.py`
- `upload_to_sheets.py`

## Template

```python
#!/usr/bin/env python3
"""
Script description here.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Main entry point."""
    pass

if __name__ == "__main__":
    main()
```
