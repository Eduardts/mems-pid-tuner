"""
datasheet_parser.py
Small helper that extracts simple parameters from a plain-text 'datasheet' file.
Expected format (example):
  ResonanceFrequency: 12000 Hz
  QFactor: 150
  Stiffness: 0.25 N/m

This is a simple parser for demonstration and must be adapted to your datasheet format.
"""
import re

def parse_datasheet(path):
    params = {}
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()

    # resonance frequency
    m = re.search(r'Resonance\s*Frequency\s*[:=]\s*([0-9\.]+)\s*Hz', text, re.IGNORECASE)
    if m:
        params['resonance_freq_hz'] = float(m.group(1))

    m = re.search(r'Q\s*Factor\s*[:=]\s*([0-9\.]+)', text, re.IGNORECASE)
    if m:
        params['q_factor'] = float(m.group(1))

    m = re.search(r'Stiffness\s*[:=]\s*([0-9\.eE\-\+]+)\s*(N\/m)?', text, re.IGNORECASE)
    if m:
        params['stiffness_N_per_m'] = float(m.group(1))

    return params

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('file', help='path to datasheet text file')
    args = p.parse_args()
    parsed = parse_datasheet(args.file)
    print("Parsed parameters:")
    for k, v in parsed.items():
        print(f"{k}: {v}")
