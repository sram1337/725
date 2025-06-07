import json
import subprocess
import sys
from decimal import Decimal, getcontext

# Set precision for Decimal calculations
getcontext().prec = 12

def main():
    """
    Evaluates a reimbursement calculation script against a set of test cases.
    This script is a Python-based, cross-platform equivalent of eval.sh.
    """
    print("🧾 Black Box Challenge - Reimbursement System Evaluation (Python Version)")
    print("=======================================================================")
    print()

    # --- 1. Check for required files ---
    try:
        with open('public_cases.json', 'r') as f:
            try:
                test_cases = json.load(f)
            except json.JSONDecodeError:
                print("❌ Error: public_cases.json is not valid JSON!")
                sys.exit(1)
    except FileNotFoundError:
        print("❌ Error: public_cases.json not found!")
        print("Please ensure the public cases file is in the current directory.")
        sys.exit(1)

    try:
        # The target script to evaluate, as per the PRD's implicit structure
        with open('run.py', 'r') as f:
            pass
    except FileNotFoundError:
        print("❌ Error: run.py not found!")
        print("Please create a run.py script that takes three command-line arguments:")
        print("  python run.py <trip_duration_days> <miles_traveled> <total_receipts_amount>")
        print("  and prints the reimbursement amount to standard output.")
        sys.exit(1)

    print(f"📊 Running evaluation against {len(test_cases)} test cases...")
    print()

    # --- 2. Initialize counters and data stores ---
    successful_runs = 0
    exact_matches = 0
    close_matches = 0
    total_error = Decimal('0')
    max_error = Decimal('-1')
    results = []
    errors = []

    # --- 3. Process each test case ---
    for i, case in enumerate(test_cases):
        if i > 0 and i % 100 == 0:
            print(f"Progress: {i}/{len(test_cases)} cases processed...")

        inputs = case['input']
        trip_duration = str(inputs['trip_duration_days'])
        miles_traveled = str(inputs['miles_traveled'])
        receipts_amount = str(inputs['total_receipts_amount'])
        expected_output = Decimal(str(case['expected_output']))

        try:
            # Execute the run.py script as a separate process
            process = subprocess.run(
                [sys.executable, 'run.py', trip_duration, miles_traveled, receipts_amount],
                capture_output=True,
                text=True,
                timeout=5 # Add a 5-second timeout
            )
            
            if process.returncode != 0:
                # Capture stderr for better error reporting
                error_msg = process.stderr.strip()
                errors.append(f"Case {i+1}: Script failed with error: {error_msg}")
                continue

            output_str = process.stdout.strip()
            
            try:
                # Validate and convert output to Decimal
                actual_output = Decimal(output_str)
            except Exception:
                errors.append(f"Case {i+1}: Invalid numeric output format: '{output_str}'")
                continue

            # --- 4. Calculate metrics ---
            successful_runs += 1
            error = abs(actual_output - expected_output)
            total_error += error
            
            results.append({
                "case_num": i + 1,
                "inputs": inputs,
                "expected": expected_output,
                "actual": actual_output,
                "error": error
            })

            if error < Decimal('0.01'):
                exact_matches += 1
            if error < Decimal('1.00'):
                close_matches += 1
            
            if error > max_error:
                max_error = error

        except subprocess.TimeoutExpired:
            errors.append(f"Case {i+1}: Script timed out after 5 seconds.")
        except Exception as e:
            errors.append(f"Case {i+1}: An unexpected error occurred: {e}")

    print(f"Progress: {len(test_cases)}/{len(test_cases)} cases processed...")
    print()

    # --- 5. Display results ---
    if successful_runs == 0:
        print("❌ No successful test cases!")
        print("\nYour script either:")
        print("  - Failed to run properly on all cases")
        print("  - Produced invalid output format")
        print("  - Timed out on all cases")
    else:
        avg_error = total_error / successful_runs
        exact_pct = (Decimal(exact_matches) / successful_runs) * 100
        close_pct = (Decimal(close_matches) / successful_runs) * 100
        
        # Calculate score (lower is better)
        score = (avg_error * 100) + (Decimal(len(test_cases) - exact_matches) * Decimal('0.1'))

        print("✅ Evaluation Complete!")
        print("\n📈 Results Summary:")
        print(f"  Total test cases: {len(test_cases)}")
        print(f"  Successful runs:  {successful_runs}")
        print(f"  Exact matches (±$0.01): {exact_matches} ({exact_pct:.1f}%)")
        print(f"  Close matches (±$1.00): {close_matches} ({close_pct:.1f}%)")
        print(f"  Average error:    ${avg_error:.2f}")
        print(f"  Maximum error:    ${max_error:.2f}")
        print(f"\n🎯 Your Score: {score:.2f} (lower is better)")
        print()
        
        # Provide feedback based on score
        if exact_matches == len(test_cases):
            print("🏆 PERFECT SCORE! You have reverse-engineered the system completely!")
        elif exact_matches > 950:
            print("🥇 Excellent! You are very close to the perfect solution.")
        elif exact_matches > 800:
            print("🥈 Great work! You have captured most of the system behavior.")
        elif exact_matches > 500:
            print("🥉 Good progress! You understand some key patterns.")
        else:
            print("📚 Keep analyzing the patterns in the interviews and test cases.")
        
        if exact_matches < len(test_cases):
            print("\n💡 Tips for improvement:")
            print("  Check these high-error cases:")
            
            # Sort results by error and show top 5
            high_error_cases = sorted(results, key=lambda x: x['error'], reverse=True)[:5]
            for r in high_error_cases:
                inp = r['inputs']
                print(f"    Case {r['case_num']}: {inp['trip_duration_days']} days, {inp['miles_traveled']} miles, ${inp['total_receipts_amount']} receipts")
                print(f"      Expected: ${r['expected']:.2f}, Got: ${r['actual']:.2f}, Error: ${r['error']:.2f}")

    # --- 6. Show script errors ---
    if errors:
        print("\n⚠️  Errors encountered during evaluation:")
        for j, err in enumerate(errors[:10]):
            print(f"  - {err}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors.")
            
    print("\n📝 Next steps:")
    print("  1. Create run.py with your solution logic.")
    print("  2. Ensure your run.py script prints ONLY the final numeric result.")
    print("  3. Analyze the high-error cases to refine your logic.")
    print("  4. Submit your solution via the Google Form when ready!")

if __name__ == "__main__":
    main() 