#!/usr/bin/env python3
"""Analyze OlmOCR generation behavior from log file"""

import re
from pathlib import Path

log_file = Path("/home/bryanjowers/pdf-rag/test_output/validation_test/scanned_output/logs/olmocr_scanned_temp.log")

print("="*70)
print("OlmOCR Generation Timeline Analysis")
print("="*70)

with open(log_file) as f:
    log_lines = f.readlines()

# Find key timestamps
print("\n🕐 GENERATION TIMELINE:\n")

timestamps = []
for line in log_lines:
    # Extract throughput info
    if "Avg prompt throughput" in line and "Avg generation throughput" in line:
        match = re.search(r'(\d{2}:\d{2}:\d{2})', line)
        if match:
            time = match.group(1)
            
            prompt_match = re.search(r'Avg prompt throughput: ([\d.]+) tokens/s', line)
            gen_match = re.search(r'Avg generation throughput: ([\d.]+) tokens/s', line)
            running_match = re.search(r'Running: (\d+) reqs', line)
            
            if prompt_match and gen_match and running_match:
                timestamps.append({
                    'time': time,
                    'prompt_tps': float(prompt_match.group(1)),
                    'gen_tps': float(gen_match.group(1)),
                    'running': int(running_match.group(1))
                })

print(f"{'Time':<12} {'Prompt T/s':<15} {'Gen T/s':<15} {'Running Reqs':<15} {'Phase'}")
print("-" * 70)

for i, ts in enumerate(timestamps):
    phase = "Startup" if i == 0 else ("Peak" if ts['running'] >= 20 else ("Winding Down" if ts['running'] > 5 else "Finishing"))
    print(f"{ts['time']:<12} {ts['prompt_tps']:>10.1f} t/s   {ts['gen_tps']:>10.1f} t/s   {ts['running']:>6} reqs     {phase}")

# Calculate generation stats
print("\n📈 GENERATION STATISTICS:\n")

total_gen_tokens = 14889
gen_duration = 170  # seconds (from log)

print(f"Total output tokens:     {total_gen_tokens:,}")
print(f"Generation duration:     {gen_duration} seconds")
print(f"Average generation rate: {total_gen_tokens/gen_duration:.1f} tokens/second")
print(f"Time per page:          {gen_duration/28:.1f} seconds")

# Estimate truncation point
digital_chars = 91235
scanned_chars = 53279
coverage_pct = (scanned_chars / digital_chars) * 100

print(f"\n📄 DOCUMENT COVERAGE:\n")
print(f"Digital output:          {digital_chars:,} chars")
print(f"Scanned output:          {scanned_chars:,} chars")
print(f"Coverage:                {coverage_pct:.1f}%")
print(f"Estimated page reached:  ~{28 * coverage_pct / 100:.0f} of 28 pages")

print("\n" + "="*70)
