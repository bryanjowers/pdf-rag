#!/usr/bin/env python3
"""Compare what's different between digital and scanned outputs"""

from pathlib import Path

digital_md = Path('/home/bryanjowers/pdf-rag/test_output/validation_test/digital_output/markdown/SDTO_170.0 ac 12-5-2022.md')
scanned_md = Path('/home/bryanjowers/pdf-rag/test_output/validation_test/scanned_temp.md')

with open(digital_md) as f:
    digital_text = f.read()

with open(scanned_md) as f:
    scanned_text = f.read()

print('='*70)
print('CHARACTER DIFFERENCE ANALYSIS')
print('='*70)

print(f'\nDigital: {len(digital_text):,} chars, {len(digital_text.split())} words')
print(f'Scanned: {len(scanned_text):,} chars, {len(scanned_text.split())} words')
print(f'Difference: {len(digital_text) - len(scanned_text):,} chars')

# Count specific formatting elements
digital_lines = digital_text.split('\n')
scanned_lines = scanned_text.split('\n')

print(f'\nDigital: {len(digital_lines)} lines')
print(f'Scanned: {len(scanned_lines)} lines')

# Count tables
digital_tables = digital_text.count('|')
scanned_tables_md = scanned_text.count('|')
scanned_tables_html = scanned_text.count('<table>')

print(f'\n' + '='*70)
print('TABLE FORMATTING')
print('='*70)
print(f'Digital markdown tables (| count): {digital_tables}')
print(f'Scanned markdown tables (| count): {scanned_tables_md}')
print(f'Scanned HTML tables (<table> count): {scanned_tables_html}')

# Count image markers
digital_images = digital_text.count('<!-- image -->')
scanned_images = scanned_text.count('![')

print(f'\n' + '='*70)
print('IMAGE MARKERS')
print('='*70)
print(f'Digital: {digital_images} <!-- image --> markers')
print(f'Scanned: {scanned_images} ![...] markers')

# Check for missing sections
print(f'\n' + '='*70)
print('SECTION COMPLETENESS')
print('='*70)

key_phrases = [
    'Assignment No. 11',
    'EXHIBIT',
    'MLJ (7120)',  # Digital has this, scanned might not
]

for phrase in key_phrases:
    in_digital = phrase in digital_text
    in_scanned = phrase in scanned_text
    status = '✅' if in_scanned else '❌'
    print(f'{status} "{phrase}": Digital={in_digital}, Scanned={in_scanned}')
