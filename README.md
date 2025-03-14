# colls.py

A custom `ls -l` wrapper with flexible column selection, custom separators, and reverse highlights for better readability. Built for Unix-like systems to enhance file listing with a focus on customization.

Built by jctratt & Grok (xAI) - March 2025.

## Features
- Select specific columns from `ls -l` output (e.g., `-951` for filename, size, permissions).
- Use custom separators with extended syntax (e.g., `--"9_5_1"` or `--"9 - 5 - 1"`).
- Toggle quotes around filenames with `-Q`.
- Show column headers with `--header`.
- Highlight large padding in filenames/targets with reverse color (configurable via `--max-pad`).

## Usage
```bash
colls.py [OPTIONS] [LS_ARGS]
