import re
import csv
import argparse
from pathlib import Path

def process_log(input_path):
    input_file = Path(input_path)
    output_file = input_file.with_suffix('.csv')

    # Patterns
    # 1. Matches "Checking on pepper..." -> Group 1: pepper
    test_name_pattern = re.compile(r"Checking on (.*?)\.\.\.")
    # 2. Matches [HH:MM:SS] and optional SNR -> Group 1: HH:MM:SS, Group 2: SNR value
    trace_pattern = re.compile(r"\[(\d{2}:\d{2}:\d{2})\].*?(?:[:\s](-?\d+\.?\d*)dB)?")

    data = []
    current_test_name = "unknown"

    try:
        with open(input_file, 'r') as infile:
            for line in infile:
                # Check if this line marks the start of a new test section
                name_match = test_name_pattern.search(line)
                if name_match:
                    current_test_name = name_match.group(1)
                    continue

                # Check if this line is a trace entry
                trace_match = trace_pattern.search(line)
                if trace_match:
                    timestamp = trace_match.group(1)
                    snr_value = trace_match.group(2) if trace_match.group(2) else "null"
                    data.append([current_test_name, timestamp, snr_value])

        # Write results to CSV
        with open(output_file, 'w', newline='') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(["test_name", "timestamp", "SNR"])
            writer.writerows(data)

        print(f"Processed {len(data)} traces from '{input_file}' into '{output_file}'.")

    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse multi-test logs into CSV.")
    parser.add_argument("input", help="Path to the input log file.")
    args = parser.parse_args()

    process_log(args.input)
