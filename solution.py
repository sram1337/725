import json
import sys
import random

def get_per_diem_total(trip_duration_days, miles_traveled, total_receipts_amount, config):
    per_diem_rate = 100
    
    # This logic corresponds to the $177.91 baseline
    if trip_duration_days > 13:
        per_diem_rate = config["per_diem_rate_14_plus_days"]
    elif trip_duration_days >= 10:
        per_diem_rate = config["per_diem_rate_10_plus_days"]
    
    return trip_duration_days * per_diem_rate

def get_mileage_total(trip_duration_days, miles_traveled):
    # This function did not take a config object in the baseline version
    primary_mileage_rate = 0.58
    secondary_mileage_rate = 0.45
    if trip_duration_days > 7:
        secondary_mileage_rate = 0.35

    if miles_traveled > 100:
        return (100 * primary_mileage_rate) + ((miles_traveled - 100) * secondary_mileage_rate)
    return miles_traveled * primary_mileage_rate

def get_receipt_total(trip_duration_days, miles_traveled, total_receipts_amount, config):
    # --- New: Special handling for short, high-cost trips ---
    path = "STANDARD"
    is_short_expensive_trip = (
        trip_duration_days <= 4 and
        total_receipts_amount > 1000
    )
    if is_short_expensive_trip:
        percentage = config.get("short_trip_high_receipt_pct", DEFAULT_CONFIG["short_trip_high_receipt_pct"])
        path = "SHORT_TRIP_HIGH_RECEIPT_BONUS"
        # For these trips, we return a simple percentage and no penalty
        return total_receipts_amount * percentage, 0, path

    # --- Original logic for all other trips ---
    if trip_duration_days == 1 and total_receipts_amount > 500:
        path = "ONE_DAY_HIGH_RECEIPT_MULTIPLIER"
        return total_receipts_amount * config.get("one_day_high_receipt_multiplier", 0.6), 0, path
    if trip_duration_days == 2 and total_receipts_amount > 500:
        path = "TWO_DAY_HIGH_RECEIPT_MULTIPLIER"
        return total_receipts_amount * config.get("two_day_high_receipt_multiplier", 0.7), 0, path

    daily_spending_limit = 0
    if 1 <= trip_duration_days <= 3:
        daily_spending_limit = 75
    elif 4 <= trip_duration_days <= 6:
        daily_spending_limit = config["receipt_cap_4_6_days"]
    
    reimbursable_receipts = total_receipts_amount
    if trip_duration_days > 0 and daily_spending_limit > 0:
        daily_spending = total_receipts_amount / trip_duration_days
        if daily_spending > daily_spending_limit:
            path = "DAILY_SPENDING_LIMIT_APPLIED"
            reimbursable_receipts = daily_spending_limit * trip_duration_days

    tier_1_threshold = config.get("receipt_tier_1_threshold", 820)
    tier_1_pct = config.get("receipt_tier_1_percentage", 0.6)
    tier_2_pct = config.get("receipt_tier_2_percentage", 0.28)
    
    # --- Tiered standard percentage based on trip duration ---
    if 1 <= trip_duration_days <= 3:
        standard_pct = config.get("standard_receipt_pct_1_3_days", 0.55)
    elif 4 <= trip_duration_days <= 6:
        standard_pct = config.get("standard_receipt_pct_4_6_days", 0.6)
    else:
        # Fallback for other durations (e.g., >= 7, but not hitting the tiered logic above)
        standard_pct = config.get("standard_receipt_pct", 0.55)

    if trip_duration_days >= 7 and reimbursable_receipts > tier_1_threshold:
        path = "TIERED_RECEIPT_OVER_600"
        receipt_total = tier_1_threshold * tier_1_pct + (reimbursable_receipts - tier_1_threshold) * tier_2_pct
    elif reimbursable_receipts > 20:
        path = "STANDARD_80_PCT"
        receipt_total = reimbursable_receipts * standard_pct
    else:
        path = "ZEROED_RECEIPT_UNDER_20"
        receipt_total = 0

    penalty = -50 if 0 < total_receipts_amount <= 20 else 0
    return receipt_total, penalty, path

def get_efficiency_bonus(trip_duration_days, miles_traveled):
    if trip_duration_days == 0:
        return 0
    miles_per_day = miles_traveled / trip_duration_days
    if 180 <= miles_per_day <= 220:
        return 50
    if miles_per_day < 100 or miles_per_day > 300:
        return -50
    return 0

# --- Configuration (from our best run) ---
DEFAULT_CONFIG = {
    "extreme_day_receipt_threshold": 1600.0,
    "extreme_day_high_receipt_pct": 0.5,
    "extreme_day_low_receipt_multiplier": 0.6,
    "per_diem_rate_10_plus_days": 70, # Tuned
    "per_diem_rate_14_plus_days": 55, # Tuned
    "receipt_cap_4_6_days": 250, # Reverting this change
    "high_cost_receipt_percentage": 0.25,
    "short_trip_high_receipt_pct": 0.5, 
    "one_day_high_receipt_multiplier": 0.6,
    "two_day_high_receipt_multiplier": 0.7,
    "receipt_tier_1_threshold": 820,
    "receipt_tier_1_percentage": 0.6,
    "receipt_tier_2_percentage": 0.28,
    "standard_receipt_pct": 0.4,
    "standard_receipt_pct_1_3_days": 0.55,
    "standard_receipt_pct_4_6_days": 0.6000000000000001,
    "per_diem_rate_long_trip": 60,
    "receipt_cap_long_trip_low": 110,
    "receipt_cap_long_trip_high": 110.0,
    "high_spend_threshold": 130.0,
    "pct_first_600": 0.75,
    "pct_above_600": 0.7000000000000001,
    "vacation_penalty_enabled": True,
    "vacation_penalty_duration_threshold": 8,
    "vacation_penalty_spend_threshold": 150.0,
    "vacation_penalty_per_diem_pct": 0.7,
    "vacation_penalty_receipt_pct": 0.44999999999999996,
}

def calculate_reimbursement(trip_duration_days, miles_traveled, total_receipts_amount, debug=False, config=DEFAULT_CONFIG):
    path = "NORMAL"
    receipt_path = None # Initialize receipt_path

    # Special case for extreme 1-day trips
    if trip_duration_days == 1 and miles_traveled > 800:
        if total_receipts_amount > config["extreme_day_receipt_threshold"]:
            path = "SPECIAL_EXTREME_ONE_DAY_HIGH_RECEIPT"
            computed_total = round(total_receipts_amount * config["extreme_day_high_receipt_pct"], 2)
        else:
            path = "SPECIAL_EXTREME_ONE_DAY_LOW_RECEIPT"
            computed_total = round((miles_traveled + total_receipts_amount) * config["extreme_day_low_receipt_multiplier"], 2)
        
        if debug:
             return {
                "path": path, "receipt_path": None, "per_diem": 0, "mileage": 0, "receipts$": computed_total, "penalty": 0, "eff_bonus": 0,
                "grand": computed_total
            }
        return computed_total

    # --- Vacation Penalty Logic (New Implementation) ---
    daily_spend = total_receipts_amount / trip_duration_days if trip_duration_days > 0 else 0
    
    vacation_penalty_active = (
        config.get("vacation_penalty_enabled", False) and
        trip_duration_days >= 8 and # Explicitly setting to 8+ days
        daily_spend > config.get("vacation_penalty_spend_threshold", 120)
    )

    if vacation_penalty_active:
        path = "VACATION_PENALTY_HIGH_SPEND"
        
        # This path should be self-contained and not call other complex logic
        per_diem_total = get_per_diem_total(trip_duration_days, miles_traveled, total_receipts_amount, config)
        mileage_total = get_mileage_total(trip_duration_days, miles_traveled)
        
        # Apply a simple, harsh penalty directly to the main components
        final_per_diem = per_diem_total * config.get("vacation_penalty_per_diem_pct", 0.5)
        final_receipts = total_receipts_amount * config.get("vacation_penalty_receipt_pct", 0.5) # Use raw receipts
        
        efficiency_bonus = get_efficiency_bonus(trip_duration_days, miles_traveled)
        computed_total = round(final_per_diem + mileage_total + final_receipts + efficiency_bonus, 2)
        
        if debug:
            return {
                "path": path, "receipt_path": "N/A", "miles_per_day": miles_traveled / trip_duration_days if trip_duration_days > 0 else 0,
                "per_diem": final_per_diem, "mileage": mileage_total, 
                "receipts$": final_receipts, "penalty": 0, "eff_bonus": efficiency_bonus, "grand": computed_total
            }
        return computed_total
        
    # --- New Two-Tier Logic for Long Trips ---
    if trip_duration_days >= 10:
        path = "LONG_TRIP_TWO_TIER"
        
        per_diem_total = trip_duration_days * config["per_diem_rate_long_trip"]
        mileage_total = get_mileage_total(trip_duration_days, miles_traveled)
        efficiency_bonus = get_efficiency_bonus(trip_duration_days, miles_traveled)

        cap_per_day = (
            config["receipt_cap_long_trip_high"]
            if (total_receipts_amount / trip_duration_days) > config["high_spend_threshold"]
            else config["receipt_cap_long_trip_low"]
        )
        max_reimbursable = cap_per_day * trip_duration_days
        reimbursable = min(total_receipts_amount, max_reimbursable)
        
        receipt_total = (
            min(reimbursable, 600) * config["pct_first_600"]
            + max(reimbursable - 600, 0) * config["pct_above_600"]
        )

        computed_total = round(per_diem_total + mileage_total + receipt_total + efficiency_bonus, 2)

        if debug:
            miles_per_day = miles_traveled / trip_duration_days if trip_duration_days > 0 else 0
            return {
                "path": path, "receipt_path": "TWO_TIER_CALC", "miles_per_day": miles_per_day,
                "per_diem": per_diem_total, "mileage": mileage_total, 
                "receipts$": receipt_total, "penalty": 0, "eff_bonus": efficiency_bonus, "grand": computed_total
            }
        return computed_total
    
    # --- Standard Calculation Logic ---
    per_diem_total = get_per_diem_total(trip_duration_days, miles_traveled, total_receipts_amount, config)
    mileage_total = get_mileage_total(trip_duration_days, miles_traveled)
    receipt_total, penalty, receipt_path = get_receipt_total(trip_duration_days, miles_traveled, total_receipts_amount, config)
    efficiency_bonus = get_efficiency_bonus(trip_duration_days, miles_traveled)

    computed_total = round(per_diem_total + mileage_total + receipt_total + penalty + efficiency_bonus, 2)

    if debug:
        miles_per_day = miles_traveled / trip_duration_days if trip_duration_days > 0 else 0
        return {
            "path": path,
            "receipt_path": receipt_path,
            "miles_per_day": miles_per_day,
            "per_diem": per_diem_total,
            "mileage": mileage_total,
            "receipts$": receipt_total,
            "penalty": penalty,
            "eff_bonus": efficiency_bonus,
            "grand": computed_total
        }

    return computed_total

if __name__ == '__main__':
    if len(sys.argv) == 4:
        trip_duration_days = int(sys.argv[1])
        miles_traveled = int(sys.argv[2])
        total_receipts_amount = float(sys.argv[3])
        
        reimbursement = calculate_reimbursement(
            trip_duration_days,
            miles_traveled,
            total_receipts_amount
        )
        print(reimbursement)
    else:
        # Running for testing with public_cases.json
        with open('public_cases.json', 'r') as f:
            cases = json.load(f)
        
        if '--filter' in sys.argv:
            filter_index = sys.argv.index('--filter') + 1
            if filter_index < len(sys.argv):
                filter_str = sys.argv[filter_index]
                original_cases = cases
                cases = []
                for case in original_cases:
                    context = case['input']
                    if eval(filter_str, {}, context):
                        cases.append(case)
                print(f"Filtered to {len(cases)} cases based on: '{filter_str}'")
        
        errors = []
        
        for case in cases:
            inputs = case['input']
            expected_output = case['expected_output']
            
            # Use the debug flag to get detailed info
            debug_info = calculate_reimbursement(
                inputs['trip_duration_days'],
                inputs['miles_traveled'],
                inputs['total_receipts_amount'],
                debug=True,
                config=DEFAULT_CONFIG # Pass config to get correct baseline
            )
            
            calculated_output = debug_info['grand']
            error = abs(calculated_output - expected_output)
            errors.append({'input': inputs, 'expected': expected_output, 'debug': debug_info, 'error': error})
            
        average_error = sum(e['error'] for e in errors) / len(cases)
        print(f"Average Error: {average_error:.2f}\n")

        # --- Path-based error analysis ---
        path_buckets = {}
        for e in errors:
            receipt_path_str = e['debug'].get('receipt_path', 'N/A')
            path_key = f"{e['debug']['path']} -> {receipt_path_str}"
            if path_key not in path_buckets:
                path_buckets[path_key] = []
            path_buckets[path_key].append(e)

        print("\nPath-based error analysis (by total error contribution):")
        path_total_errors = {name: sum(err['error'] for err in errs) for name, errs in path_buckets.items()}
        sorted_paths = sorted(path_buckets.items(), key=lambda item: path_total_errors[item[0]], reverse=True)

        for path_name, path_errors in sorted_paths:
            count = len(path_errors)
            if count > 0:
                total_error_in_path = path_total_errors[path_name]
                avg_error_in_path = total_error_in_path / count
                print(f"  - Path: {path_name:<50} | Cases: {count:<4} | Total Error: ${total_error_in_path:<8.2f} | Avg Error: ${avg_error_in_path:<8.2f}")

        # --- Focused analysis on the highest-contributing path ---
        if sorted_paths:
            highest_impact_path_name, target_path_errors = sorted_paths[0]
            
            if not target_path_errors:
                print("\nNo significant errors to analyze. Great job!")
                sys.exit()

            print(f"\nAnalysis of Highest-Error Path: '{highest_impact_path_name}' ({len(target_path_errors)} cases)")
            
            # Take a random sample to avoid bias
            sample_size = min(5, len(target_path_errors)) # Show top 5
            random_sample = random.sample(target_path_errors, sample_size)
            
            for e in random_sample:
                print(f"Input: {e['input']}, Expected: {e['expected']:.2f}, Error: {e['error']:.2f}")
                print(f"  Debug Info: {e['debug']}")
                print("-" * 20) 