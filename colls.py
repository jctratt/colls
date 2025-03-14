#!/usr/bin/env python3
# colls.py - A custom ls -l wrapper with flexible column selection and formatting.
# Copyright (C) 2025 jctratt & Grok (xAI)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import subprocess
import sys
import re

def strip_ansi_codes(text):
    """Remove ANSI color codes from a string."""
    return re.sub(r'\x1b\[[0-9;]*[mK]', '', text)

def get_color_code(text):
    """Extract the last ANSI color code before any reset."""
    matches = list(re.finditer(r'\x1b\[([0-9;]*)m', text))
    for match in reversed(matches):
        code = match.group(1)
        if code != '0':  # Ignore reset codes
            return f"\x1b[{code}m"
    return ''

def strip_quotes_python(col, keep_indicator=True):
    """Strip outer quotes added by ls -lQ, preserving ANSI codes, internal quotes, and indicators."""
    if not col:
        return col

    # Get clean text for quote detection
    clean = strip_ansi_codes(col)
    if not (clean.startswith('"') and '"' in clean[1:]):
        return col

    # Define indicators
    indicators = '*/@|='

    # Find outer quotes in original string
    start = col.find('"')
    end = col.rfind('"') + 1

    # Extract content between outer quotes (actual filename)
    content = col[start + 1:end - 1]

    # Check for indicator immediately after the closing quote
    indicator = ''
    if end < len(col) and col[end] in indicators:
        indicator = col[end]

    # Reconstruct:
    # - ANSI codes before first quote
    # - Content (filename, may have internal quotes)
    # - Indicator if present and requested
    # - Remaining ANSI codes after indicator
    result = col[:start] + content
    if keep_indicator and indicator:
        result += indicator
    # Only append remaining ANSI codes if they exist after indicator
    ansi_tail = col[end + len(indicator):] if end + len(indicator) < len(col) else ''
    if ansi_tail and not ansi_tail.startswith('"'):  # Avoid adding stray quotes
        result += ansi_tail

    return result

def split_line_into_columns(line):
    """Split an ls -lQ line into 11 columns (0-10, filename at 8, arrow at 9, target at 10)."""
    parts = line.strip().split(maxsplit=8)
    if len(parts) < 9:
        parts.extend([""] * (9 - len(parts)))
    filename_part = parts[8]
    if ' -> ' in strip_ansi_codes(filename_part):
        filename, rest = filename_part.split(' -> ', 1)
        arrow = "->"
        target = rest
    else:
        filename, arrow, target = filename_part, " ", " "
    return [
        parts[0], parts[1], parts[2], parts[3], parts[4],
        parts[5], parts[6], parts[7], filename, arrow, target
    ]

def calculate_column_widths(lines, strip_quotes=False):
    """Calculate max width for each column, including special cases for 0 and *."""
    widths = [0] * 11
    extra_widths = {'0': 4, '*': 0}
    for line in lines:
        columns = split_line_into_columns(line)
        if len(columns) == 11:
            filename = strip_quotes_python(columns[8], keep_indicator=True) if strip_quotes else columns[8]
            arrow = strip_ansi_codes(columns[9])
            target = strip_quotes_python(columns[10], keep_indicator=True) if strip_quotes else columns[10]
            for i, col in enumerate(columns):
                if i == 8:
                    display_col = strip_ansi_codes(filename)
                elif i == 9:
                    display_col = arrow
                    extra_widths['0'] = max(extra_widths['0'], len(display_col))
                elif i == 10:
                    display_col = strip_ansi_codes(target)
                    extra_widths['*'] = max(extra_widths['*'], len(display_col))
                else:
                    display_col = strip_ansi_codes(col)
                widths[i] = max(widths[i], len(display_col))
    return widths, extra_widths

def print_header(widths, extra_widths, columns_to_show, separators):
    """Print header with column indices, using multiple separators."""
    header_parts = []
    for i in columns_to_show:
        if i in '123456789':
            col_idx = int(i) - 1
            header_parts.append(str(i).ljust(widths[col_idx]))
        elif i == '0':
            header_parts.append('0'.ljust(extra_widths['0']))
        elif i == '*':
            header_parts.append('*'.ljust(extra_widths['*']))
    output = header_parts[0]
    for i, part in enumerate(header_parts[1:], 1):
        sep = separators[i-1] if i-1 < len(separators) else " "
        output += sep + part
    print(output)

def print_version():
    """Print version and GPL interactive notice."""
    print("""
colls.py version 1.0.0
Copyright (C) 2025 jctratt & Grok (xAI)
This program comes with ABSOLUTELY NO WARRANTY; for details type `colls.py --help`.
This is free software, and you are welcome to redistribute it
under certain conditions; type `colls.py --help` for details.
""")

def print_help():
    """Print detailed help message."""
    help_text = """
Usage: colls.py [OPTIONS] [LS_ARGS]

colls.py - A custom ls -l wrapper with flexible column selection and formatting.
Built by jctratt & Grok (xAI) - March 2025

Options:
  -[1234567890*]    Select columns to display (e.g., -951 for columns 9, 5, 1).
                     Uses single space as separator.
  --"COLS[SEP]COLS" Extended syntax to select columns with custom separators
                     (e.g., --"9_5_1" or --"9 - 5 - 1").
  -Q                 Show filenames with quotes (default: quotes stripped).
  --header           Show column headers above the listing.
  --max-pad N        Set max padding for reverse highlight (default: 5, 0 to disable).
  --version          Display version and license information.
  --help             Display this help message.

Columns:
  1: Permissions (e.g., lrwxrwxrwx)
  2: Number of links
  3: Owner name
  4: Group name
  5: Size in bytes (human-readable)
  6: Month of last modification
  7: Day of last modification
  8: Time/year of last modification
  9: Filename (colored if symlink or dir)
  0: Arrow (" -> ") for symlinks, spaces otherwise
  *: Symlink target (if applicable), spaces otherwise

Examples:
  colls.py -91           Show filename and permissions.
  colls.py --"9_5_1" --header  Show filename, size, perms with "_" separators.
  colls.py --"9 - 5 - 1"  Show filename, size, perms with " - " separators.
  colls.py -951 -Q       Show filename, size, perms with quotes.
  colls.py dir1 dir2     List specific directories.

Notes:
- Uses /bin/ls to bypass aliases, ensuring consistent output.
- Colors are preserved from ls --color=always.
- Reverse highlight (e.g., alice<rev>   <off>) applied to filenames/targets with padding >= --max-pad when followed by content.
- Trailing count shows number of files found.
"""
    print(help_text.strip())

def main():
    cmd = ["/bin/ls", "--color=always", "-lQAhF"]  # Keep -F for indicators
    args = sys.argv[1:]

    if "--version" in args:
        print_version()
        sys.exit(0)

    if "--help" in args:
        print_help()
        sys.exit(0)

    use_quotes = "-Q" in args
    show_header = "--header" in args
    max_pad = 5
    for i, arg in enumerate(args[:]):
        if arg == "--max-pad" and i + 1 < len(args):
            try:
                max_pad = int(args[i + 1])
                args.pop(i + 1)
                args.pop(i)
                break
            except ValueError:
                print("Error: --max-pad requires an integer.", file=sys.stderr)
                sys.exit(1)

    ls_args = []
    format_args = []
    for arg in args:
        if arg.startswith("-") and all(c in "1234567890*" for c in arg[1:]):
            format_args.append(arg)
        elif arg.startswith("--") and any(c in "1234567890*" for c in arg[2:]):
            format_args.append(arg)
        elif arg not in ["-Q", "--header"]:
            ls_args.append(arg)

    # Default to all columns if no format args provided
    columns_to_show = list("1234567890*") if not format_args else list("1234567890*")
    separators = [" "] * (len(columns_to_show) - 1)
    for arg in format_args:
        if arg.startswith("--"):
            raw_arg = arg[2:]
            columns_to_show = [c for c in raw_arg if c in "1234567890*"]
            parts = re.split(r'([1234567890*])', raw_arg)
            separators = []
            for i, part in enumerate(parts[1:], 1):
                if part in "1234567890*" and i < len(parts) - 1:
                    sep = parts[i+1] if i+1 < len(parts) else " "
                    if sep in "1234567890*":
                        sep = " "
                    separators.append(sep)
        elif arg.startswith("-"):
            columns_to_show = list(arg[1:])
            separators = [" "] * (len(columns_to_show) - 1)

    result = subprocess.run(cmd + ls_args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running ls: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    lines = result.stdout.splitlines()

    if lines and lines[0].startswith("total"):
        print(lines[0])
        lines = lines[1:]

    # Always strip quotes for width calculation to avoid quote width affecting padding
    widths, extra_widths = calculate_column_widths(lines, strip_quotes=True)

    if show_header:
        print_header(widths, extra_widths, columns_to_show, separators)

    file_count = 0
    for line in lines:
        columns = split_line_into_columns(line)
        if len(columns) == 11:
            file_count += 1
            display_cols = columns.copy()
            # Strip quotes from filename and target unless user explicitly wants quotes
            if not use_quotes:
                display_cols[8] = strip_quotes_python(columns[8], keep_indicator=True)
                display_cols[10] = strip_quotes_python(columns[10], keep_indicator=True) if strip_ansi_codes(columns[10]).strip() else columns[10]
            output_cols = []
            for col in columns_to_show:
                if col in '123456789':
                    output_cols.append(display_cols[int(col) - 1])
                elif col == '0':
                    arrow_clean = strip_ansi_codes(display_cols[10]).strip()
                    output_cols.append(" -> " if arrow_clean else "    ")
                elif col == '*':
                    target_clean = strip_ansi_codes(display_cols[10]).strip()
                    output_cols.append(display_cols[10] if target_clean else " " * extra_widths['*'])
            selected_padded = []
            has_following = False
            for i, c in enumerate(columns_to_show):
                if c in '123456789' or c == '*':
                    col_idx = int(c) - 1 if c in '123456789' else 10
                    col = output_cols[i]
                    visible_len = len(strip_ansi_codes(col))
                    padding_len = (widths[col_idx] if c in '123456789' else extra_widths['*']) - visible_len
                    has_following = (i < len(columns_to_show) - 1 and
                                   columns_to_show[i+1] in '1234567890*' and
                                   strip_ansi_codes(output_cols[i+1]).strip())
                    if (c == '9' or c == '*') and max_pad > 0 and padding_len >= max_pad and has_following:
                        color = get_color_code(col)
                        padding = f"{color}\x1b[7m{' ' * padding_len}\x1b[27m\x1b[0m"
                        if i < len(selected_padded) and color:
                            selected_padded[-1] = selected_padded[-1] + color
                    else:
                        padding = " " * padding_len
                    selected_padded.append(col + padding)
                elif c == '0':
                    selected_padded.append(output_cols[i].ljust(extra_widths['0']))
            output = selected_padded[0]
            for i, part in enumerate(selected_padded[1:], 1):
                sep = separators[i-1] if i-1 < len(separators) else " "
                output += sep + part
            print(output)
        else:
            print(line)

    print(f"{file_count} found")

if __name__ == "__main__":
    main()
