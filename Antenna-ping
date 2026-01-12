import subprocess
import re
import time
import statistics
import argparse

def get_node_list(port=None):
    """Fetches the current node list from the device."""
    cmd = ['meshtastic', '--nodes']
    if port:
        cmd.extend(['--port', port])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout
    except Exception as e:
        print(f"Error fetching node list: {e}")
        return ""

def is_node_direct(node_id, node_list_output):
    """
    Checks if the node_id exists in the local node DB and appears to be 0 hops away.
    The CLI table typically has a 'Hops away' or 'SNR' column for direct neighbors.
    """
    # Clean ID for matching (strip '!' if user provided it)
    clean_id = node_id.replace('!', '').lower()
    
    # Check if node exists in the output at all
    if clean_id not in node_list_output.lower():
        return False, "Node not found in local node DB."

    # Look for the specific line for this node to check distance
    # In 2026 CLI, the table includes 'Hops Away'
    for line in node_list_output.splitlines():
        if clean_id in line.lower():
            # Basic check: a direct neighbor usually shows '0' hops away
            # or has a valid SNR value without a 'via' relay.
            if " 0 " in line: 
                return True, "Node verified as 0 hops away."
            else:
                return False, f"Node found but appears to be multi-hop: {line.strip()}"
                
    return False, "Node reachability status unclear."

def run_traceroute(node_id, port=None):
    """Executes a single traceroute and parses SNR values."""
    cmd = ['meshtastic']
    if port:
        cmd.extend(['--port', port])
    cmd.extend(['--traceroute', node_id])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        output = result.stdout
        snr_matches = re.findall(r'\(([-+]?\d*\.?\d+)dB\)', output)
        return [float(s) for s in snr_matches] if snr_matches else None
    except Exception:
        return None

def main():
    parser = argparse.ArgumentParser(description="Automate Meshtastic traceroutes for direct neighbors.")
    parser.add_argument("target", help="Target Node ID (e.g., '!ba4bf9d0')")
    parser.add_argument("-i", "--iterations", type=int, default=8, help="Number of traces (default: 8)")
    parser.add_argument("-m", "--minutes", type=float, default=15.0, help="Minutes between traces (default: 15)")
    parser.add_argument("-p", "--port", help="Serial port (e.g., 'COM3')")

    args = parser.parse_args()

    # Step 1: Pre-check Reachability
    print(f"Checking if {args.target} is a direct neighbor...")
    node_data = get_node_list(args.port)
    is_direct, message = is_node_direct(args.target, node_data)
    
    if not is_direct:
        print(f"Aborting: {message}")
        return

    print(f"Success: {message}\nStarting {args.iterations} iterations...")

    # Step 2: Run Traceroutes
    outbound_history, inbound_history = [], []
    delay_seconds = args.minutes * 60

    for i in range(args.iterations):
        print(f"[{time.strftime('%H:%M:%S')}] Trace {i+1}/{args.iterations}:", end=" ", flush=True)
        snrs = run_traceroute(args.target, args.port)
        
        if snrs and len(snrs) >= 2:
            outbound_history.append(snrs[0])
            inbound_history.append(snrs[-1])
            print(f"OK (Out: {snrs[0]}dB, In: {snrs[-1]}dB)")
        else:
            print("FAILED (Route lost or timed out)")
        
        if i < args.iterations - 1:
            time.sleep(delay_seconds)

    # Step 3: Average Results
    if outbound_history:
        print(f"\n--- Final Averages ---")
        print(f"Outbound: {statistics.mean(outbound_history):.2f} dB")
        print(f"Inbound:  {statistics.mean(inbound_history):.2f} dB")

if __name__ == "__main__":
    main()
