import json
from itertools import product
from solution import calculate_reimbursement, DEFAULT_CONFIG
import numpy as np

# This now represents logical groups of parameters for coordinate descent.
PARAM_GROUPS = {
    "Per Diem Rates": [
        "per_diem_rate_10_plus_days",
        "per_diem_rate_14_plus_days",
        "per_diem_floor_rate",
        "per_diem_floor_duration",
    ],
    "Mileage Rates & Breakpoints": [
        "mileage_rate_tier_1",
        "mileage_rate_tier_2",
        "mileage_rate_tier_3",
        "mileage_breakpoint_1",
        "mileage_breakpoint_2",
    ],
    "Receipt Caps & Percentages": [
        "receipt_cap_4_6_days",
        "high_cost_receipt_percentage",
        "short_trip_high_receipt_pct",
        "receipt_tier_1_threshold",
        "receipt_tier_1_percentage",
        "receipt_tier_2_percentage",
        "standard_receipt_pct_1_3_days",
        "standard_receipt_pct_4_6_days",
    ],
    "Specific Day Multipliers": [
        "one_day_high_receipt_multiplier",
        "one_day_upper_tier_threshold",
        "one_day_upper_tier_multiplier",
        "two_day_high_receipt_multiplier",
        "two_day_upper_tier_threshold",
        "two_day_upper_tier_multiplier",
    ],
    "Extreme Day Logic": [
        "extreme_day_receipt_threshold",
        "extreme_day_high_receipt_pct",
        "extreme_day_low_receipt_multiplier",
    ],
    "Vacation Penalty": [
        "vacation_penalty_duration_threshold",
        "vacation_penalty_spend_threshold",
        "vacation_penalty_per_diem_pct",
        "vacation_penalty_receipt_pct"
    ],
    "Long Trip Tiers": [
        "per_diem_rate_long_trip",
        "receipt_cap_long_trip_low",
        "receipt_cap_long_trip_high",
        "high_spend_threshold",
        "long_trip_duration_threshold",
    ],
    "Main Receipt Logic": [
        "receipt_low_tier_threshold",
        "receipt_sweet_spot_lower_bound",
        "receipt_sweet_spot_upper_bound",
        "receipt_low_tier_pct",
        "receipt_standard_pct",
        "receipt_sweet_spot_pct",
        "receipt_high_tier_diminishing_pct"
    ],
    "Efficiency Bonus": ["eff_slope"],
}

# Define the search space for each parameter we might want to tune.
PARAM_SEARCH_SPACE = {
    # Per Diem Rates
    "per_diem_rate_10_plus_days": np.linspace(60, 80, 10),
    "per_diem_rate_14_plus_days": np.linspace(45, 65, 10),
    "per_diem_floor_rate": np.linspace(50, 70, 10),
    "per_diem_floor_duration": [12, 13, 14, 15, 16, 17],

    # Mileage Rates & Breakpoints
    "mileage_rate_tier_1": np.linspace(0.40, 0.50, 10),
    "mileage_rate_tier_2": np.linspace(0.35, 0.45, 10),
    "mileage_rate_tier_3": np.linspace(0.35, 0.45, 10),
    "mileage_breakpoint_1": np.linspace(500, 700, 10),
    "mileage_breakpoint_2": np.linspace(750, 850, 10),

    # Receipt Caps & Percentages
    "receipt_cap_4_6_days": np.linspace(200, 300, 10),
    "high_cost_receipt_percentage": np.linspace(0.20, 0.30, 10),
    "short_trip_high_receipt_pct": np.linspace(0.4, 0.6, 10),
    "receipt_tier_1_threshold": np.linspace(800, 1000, 10),
    "receipt_tier_1_percentage": np.linspace(0.5, 0.7, 10),
    "receipt_tier_2_percentage": np.linspace(0.1, 0.3, 10),
    "standard_receipt_pct_1_3_days": np.linspace(0.50, 0.60, 10),
    "standard_receipt_pct_4_6_days": np.linspace(0.55, 0.65, 10),

    # Specific Day Multipliers
    "one_day_high_receipt_multiplier": np.linspace(0.4, 0.6, 10),
    "one_day_upper_tier_threshold": np.linspace(700, 900, 10),
    "one_day_upper_tier_multiplier": np.linspace(0.5, 0.7, 10),
    "two_day_high_receipt_multiplier": np.linspace(0.4, 0.6, 10),
    "two_day_upper_tier_threshold": np.linspace(700, 900, 10),
    "two_day_upper_tier_multiplier": np.linspace(0.6, 0.8, 10),

    # Extreme Day Logic
    "extreme_day_receipt_threshold": np.linspace(1400, 1800, 10),
    "extreme_day_high_receipt_pct": np.linspace(0.4, 0.6, 10),
    "extreme_day_low_receipt_multiplier": np.linspace(0.5, 0.7, 10),
    
    # Vacation Penalty
    "vacation_penalty_duration_threshold": [8, 9, 10, 11, 12, 13, 14],
    "vacation_penalty_spend_threshold": np.linspace(130, 170, 10),
    "vacation_penalty_per_diem_pct": np.linspace(0.6, 0.8, 10),
    "vacation_penalty_receipt_pct": np.linspace(0.4, 0.5, 10),

    # Long Trip Tiers
    "per_diem_rate_long_trip": np.linspace(50, 70, 10),
    "receipt_cap_long_trip_low": np.linspace(100, 120, 10),
    "receipt_cap_long_trip_high": np.linspace(110, 130, 10),
    "high_spend_threshold": np.linspace(130, 150, 10),
    "long_trip_duration_threshold": [8, 9, 10, 11, 12, 13],

    # Main Receipt Logic
    "receipt_low_tier_threshold": np.linspace(250, 350, 10),
    "receipt_sweet_spot_lower_bound": np.linspace(650, 750, 10),
    "receipt_sweet_spot_upper_bound": np.linspace(700, 800, 10),
    "receipt_low_tier_pct": np.linspace(0.01, 0.1, 10),
    "receipt_standard_pct": np.linspace(0.3, 0.5, 10),
    "receipt_sweet_spot_pct": np.linspace(0.8, 0.9, 10),
    "receipt_high_tier_diminishing_pct": np.linspace(0.1, 0.3, 10),

    # Efficiency Bonus
    "eff_slope": np.linspace(0.3, 0.5, 10),
}

def get_path_errors(config, cases):
    """Calculates errors and groups them by calculation path."""
    errors = []
    path_buckets = {}
    for case in cases:
        inputs = case['input']
        expected = case['expected_output']
        debug_info = calculate_reimbursement(
            inputs['trip_duration_days'], inputs['miles_traveled'], inputs['total_receipts_amount'], 
            debug=True, config=config
        )
        error = abs(debug_info['grand'] - expected)
        e = {'input': inputs, 'expected': expected, 'debug': debug_info, 'error': error}
        
        receipt_path_str = debug_info.get('receipt_path', 'N/A')
        path_key = f"{debug_info['path']}"
        if debug_info['path'] == "NORMAL":
            path_key += f" -> {receipt_path_str}"
        elif debug_info['path'] == "LONG_TRIP_TWO_TIER":
            path_key += f" -> {receipt_path_str}"
        
        if path_key not in path_buckets:
            path_buckets[path_key] = []
        path_buckets[path_key].append(e)
        errors.append(e)
    
    path_total_errors = {name: sum(err['error'] for err in errs) for name, errs in path_buckets.items()}
    sorted_paths = sorted(path_buckets.items(), key=lambda item: path_total_errors[item[0]], reverse=True)
    
    total_error = sum(e['error'] for e in errors) if errors else 0
    avg_error = total_error / len(cases) if cases else 0
    
    return avg_error, sorted_paths

def main():
    with open('public_cases.json', 'r') as f:
        cases = json.load(f)

    current_best_config = DEFAULT_CONFIG.copy()
    
    print(f"\n--- Starting Iterative Tuning ---")
    
    last_error, _ = get_path_errors(current_best_config, cases)
    print(f"Starting with baseline average error: {last_error:.2f}")

    MAX_ITERATIONS = 10
    MIN_IMPROVEMENT = 0.01

    for i in range(MAX_ITERATIONS):
        print(f"\n--- Iteration {i+1}/{MAX_ITERATIONS} ---")
        error_at_start_of_iteration = last_error
        
        # Tune parameter groups
        for group_name, params_to_tune in PARAM_GROUPS.items():
            
            print(f"\n...Tuning Group '{group_name}'...")
            
            params_to_tune_filtered = [p for p in params_to_tune if p in PARAM_SEARCH_SPACE]
            if len(params_to_tune_filtered) != len(params_to_tune):
                 print(f"  > Warning: Some params for this group are not in search space and will be skipped.")
            
            # --- Tune parameters one by one (Coordinate Descent) ---
            best_group_config = current_best_config.copy()
            
            for param_to_tune in params_to_tune_filtered:
                best_param_value = best_group_config[param_to_tune]
                # Calculate error with the current best params for this group
                best_param_error = sum(abs(calculate_reimbursement(**c['input'], config=best_group_config) - c['expected_output']) for c in cases)

                search_space = PARAM_SEARCH_SPACE[param_to_tune]
                
                for value in search_space:
                    test_config = best_group_config.copy()
                    test_config[param_to_tune] = value
                    
                    total_error_for_value = sum(abs(calculate_reimbursement(**c['input'], config=test_config) - c['expected_output']) for c in cases)

                    if total_error_for_value < best_param_error:
                        best_param_error = total_error_for_value
                        best_param_value = value
                
                # Update the config for the next parameter in the group
                best_group_config[param_to_tune] = best_param_value

            # Update the main config with the best found for the group
            initial_group_error = sum(abs(calculate_reimbursement(**c['input'], config=current_best_config) - c['expected_output']) for c in cases)
            final_group_error = sum(abs(calculate_reimbursement(**c['input'], config=best_group_config) - c['expected_output']) for c in cases)

            if final_group_error < initial_group_error:
                changed_params = {p: best_group_config[p] for p in params_to_tune_filtered if current_best_config[p] != best_group_config[p]}
                if changed_params:
                    print(f"  > Found better params for this group: {changed_params}")
                current_best_config = best_group_config.copy()
        
        # Check overall improvement after a full pass
        current_error, _ = get_path_errors(current_best_config, cases)
        print(f"\n--- End of Iteration {i+1} ---")
        print(f"Average error after this pass: {current_error:.2f}")
        
        improvement = error_at_start_of_iteration - current_error
        if improvement < MIN_IMPROVEMENT:
            print(f"Improvement ({improvement:.2f}) is less than threshold ({MIN_IMPROVEMENT}). Stopping.")
            break
        last_error = current_error

    print("\n--- Tuning Complete ---")
    print("Best configuration found:")
    for key, value in current_best_config.items():
        if DEFAULT_CONFIG.get(key) != value:
            original_value = DEFAULT_CONFIG.get(key, 'N/A')
            print(f"  - {key}: {value} (Original: {original_value})")

if __name__ == '__main__':
    main()