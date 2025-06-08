import sys
import subprocess

def main():
    """
    A simple pass-through script that executes solution.py with the provided arguments.
    """
    if len(sys.argv) != 4:
        print("Usage: python run.py <trip_duration_days> <miles_traveled> <total_receipts_amount>", file=sys.stderr)
        sys.exit(1)

    # Prepare the command to execute solution.py
    command = [
        "python", 
        "solution.py", 
        sys.argv[1], 
        sys.argv[2], 
        sys.argv[3]
    ]

    try:
        # Execute the command and capture the output
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            check=True  # This will raise an exception if solution.py fails
        )
        # Print the output from solution.py, which should be the final reimbursement amount
        print(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        # If solution.py exits with an error, print its stderr for debugging
        print(f"Error executing solution.py:\n{e.stderr}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 