import json
from itertools import product
from solution import calculate_reimbursement, DEFAULT_CONFIG

# Define the parameters we want to tune
THINGS_TO_TUNE = {
    # Keep the ones we already optimized, but fix their values
    "extreme_day_receipt_threshold": [1800],
    "extreme_day_high_receipt_pct": [0.4],
    "extreme_day_low_receipt_multiplier": [0.6],

    # Parameters from the last successful run
    "receipt_cap_4_6_days": [250],
    "receipt_cap_7_plus_days": [90],
    "apply_vacation_penalty": [False],

    # New parameters for more nuanced tuning
    "apply_nuanced_vacation_penalty": [False],
    "nuanced_vacation_penalty_rate": [50, 25, 0],
    "per_diem_rate_10_plus_days": [75],
    "per_diem_rate_14_plus_days": [50],

    # Test the new hypotheses
    "zero_per_diem_vacation_penalty": [True, False],
    "round_each_step": [True, False],
}

def run_eval_with(config, cases):
    total_error = 0
    for case in cases:
        inputs = case['input']
        expected_output = case['expected_output']
        
        calculated_output = calculate_reimbursement(
            inputs['trip_duration_days'],
            inputs['miles_traveled'],
            inputs['total_receipts_amount'],
            config=config
        )
        
        error = abs(calculated_output - expected_output)
        total_error += error
        
    return total_error / len(cases)


def main():
    with open('public_cases.json', 'r') as f:
        cases = json.load(f)

    best_combo, best_err = None, float('inf')

    param_names = list(THINGS_TO_TUNE.keys())
    param_values = list(THINGS_TO_TUNE.values())
    
    all_combos = list(product(*param_values))
    print(f"Starting grid search... Testing {len(all_combos)} combinations.")

    for i, values in enumerate(all_combos):
        # Start with default config and override with tuned values
        current_config = DEFAULT_CONFIG.copy()
        current_config.update(dict(zip(param_names, values)))
        
        err = run_eval_with(current_config, cases)
        
        if (i + 1) % 20 == 0:
            print(f"  ...tested {i+1}/{len(all_combos)} combos (current best error: {best_err:.2f})")

        if err < best_err:
            best_err = err
            best_combo = current_config

    print("\n--- Grid Search Complete ---")
    print(f"Lowest average error: {best_err:.2f}")
    print("Best combination found:")
    for key, value in best_combo.items():
        print(f"  - {key}: {value}")


if __name__ == '__main__':
    main() 