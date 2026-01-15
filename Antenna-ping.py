import subprocess
import re
import time
import statistics
import argparse
import sys
import pprint

#################################################################################################################
def get_node_list(port=None, host=None):
    """Fetches the current node list from the device."""
    cmd = ['meshtastic', '--nodes']
    if port:
        cmd.extend(['--port', port])
    if host:
        cmd.extend(['--host', host])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=65)
        return result.stdout
    except Exception as e:
        print(f"Error fetching node list: {e}")
        return ""

#################################################################################################################
def get_node_info(node_id, node_list_output):
    """
    Find and parse a single node's data from a table-like string.

    :param node_id: Substring to match in User, ID, or AKA columns.
    :param node_list_output: The full table as a string.
    :return: List of parsed values for the matching row, or None if not found.
    """
    # Normalize search term
    search_term = node_id.lower()

    # Split into lines
    lines = node_list_output.splitlines()

    # Extract header line (the one with column names)
    header_line = next((line for line in lines if "User" in line and "ID" in line), None)
    if not header_line:
        return None

    # Get column names from header
    columns = [col.strip() for col in header_line.split("│") if col.strip()]

    # Filter data lines (skip header and separators)
    data_lines = [line for line in lines if line.strip().startswith("│") and "│" in line and "User" not in line]

    # Search for the line containing node_id (case-insensitive)
    for line in data_lines:
        if search_term in line.lower():
            # Split row into parts
            parts = [p.strip() for p in line.split("│") if p.strip()]
            # Map columns to values
            return dict(zip(columns, parts))

    return None

#################################################################################################################
def run_traceroute(node_id, port=None, host=None):
    """Executes a single traceroute and parses the return SNR value if direct"""
    cmd = ['meshtastic']
    if port:
        cmd.extend(['--port', port])
    if host:
        cmd.extend(['--host', host])
    cmd.extend(['--timeout 60'])
    cmd.extend(['--traceroute', node_id])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=65)
        lines = result.stdout.splitlines()

        # Find the line that starts with "Route traced back to us:"
        back_line_index = next((i for i, line in enumerate(lines) if "Route traced back to us:" in line), None)
        if back_line_index is None or back_line_index + 1 >= len(lines):
            return None, "Route lost or timed out"

        # The actual route back is on the next line
        route_back = lines[back_line_index + 1].strip()

        # Split hops by "-->"
        hops = [hop.strip() for hop in route_back.split("-->")]

        # If only two nodes (start and destination), then single hop
        if len(hops) == 2:
            # Extract SNR from the last hop (should be in parentheses like (-7.0dB))
            match = re.search(r"\(([-+]?\d*\.?\d+)dB\)", hops[-1])
            if match:
                return float(match.group(1)), "OK"
        elif len(hops) > 2:
            return None, "FAIL: Reponse not direct"
        # length of hops < 2?
        return None, "FAIL: no hops"

    except Exception:
        return None, "FAIL: Exception"
#################################################################################################################
def main():
    parser = argparse.ArgumentParser(description="Automate Meshtastic traceroutes for direct neighbors.")
    parser.add_argument("target", help="Target Node ID (any part of the ID, name, or short name)")
    parser.add_argument("-r", "--repeat", type=int, default=8, help="Number of traces (default: 8)")
    parser.add_argument("-m", "--minutes", type=float, default=15.0, help="Minutes between traces (default: 15)")
    parser.add_argument("-p", "--port", help="Serial port (e.g., 'COM3')")
    parser.add_argument("--host", help="Host IP/Name")
    parser.add_argument("-i", "--info", action="store_true", help="Get node info")
    parser.add_argument("-q", "--quiet", action="store_true", help="Only print the final result")

    args = parser.parse_args()


    # Step 1: Pre-check Reachability
    print(f"Checking on {args.target}...")
    node_data = get_node_list(args.port, args.host)
    node_info = get_node_info(args.target, node_data)

    if args.info:
        pprint.pp(node_info)

    # check that the target node is heard directly (0 hops)
    if int(node_info["Hops"]) > 0:
        print(f"Aborting: Target is not direct")
        sys.exit()
    else:
        if not args.quiet: print(f"Target is direct, ", end="")

    if not args.quiet: print(f"Starting {args.repeat} iterations, every {args.minutes} minutes...")

    # Step 2: Run Traceroutes
    inbound_history = []
    delay_seconds = args.minutes * 60

    for i in range(args.repeat):
        if not args.quiet: print(f"[{time.strftime('%H:%M:%S')}] Trace {i+1}/{args.repeat}:", end=" ", flush=True)
        snr, message = run_traceroute(node_info['ID'], args.port, args.host)

        if snr:
            inbound_history.append(snr)
            if not args.quiet: print(f"{message}: {snr}dB", flush=True)
        else:
            if not args.quiet: print(f"{message}", flush=True)

        if i < args.repeat - 1:
            time.sleep(delay_seconds)

    # Step 3: Average Results
    if inbound_history:
        print(f"Avg Inbound for {args.target}:  {statistics.mean(inbound_history):.2f} dB")

if __name__ == "__main__":
    main()
