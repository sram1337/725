import json
import sys
import random
from decimal import Decimal
import re

# --- Configuration (from our best run) ---
DEFAULT_CONFIG = {
    "per_diem_rate_10_plus_days": 80.00,
    "per_diem_rate_14_plus_days": 60.56,
    "mileage_rate_tier_1": 0.4111,
    "mileage_rate_tier_2": 0.45,
    "mileage_rate_tier_3": 0.35,
    "mileage_breakpoint_1": 522.22,
    "mileage_breakpoint_2": 750.00,
    "receipt_cap_4_6_days": 250, # Legacy, not tuned in final run
    "high_cost_receipt_percentage": 0.25, # Legacy, not tuned
    "short_trip_high_receipt_pct": 0.5, # Legacy, not tuned
    "one_day_high_receipt_multiplier": 0.40,
    "one_day_upper_tier_threshold": 700.00,
    "one_day_upper_tier_multiplier": 0.5444,
    "two_day_high_receipt_multiplier": 0.51,
    "two_day_upper_tier_threshold": 700.00,
    "two_day_upper_tier_multiplier": 0.60,
    "receipt_tier_1_threshold": 900.00, # Legacy
    "receipt_tier_1_percentage": 0.60, # Legacy
    "receipt_tier_2_percentage": 0.20, # Legacy
    "standard_receipt_pct_1_3_days": 0.55, # Legacy
    "standard_receipt_pct_4_6_days": 0.60, # Legacy
    "per_diem_rate_long_trip": 58.89,
    "receipt_cap_long_trip_low": 120.00,
    "receipt_cap_long_trip_high": 110.00,
    "high_spend_threshold": 150.00,
    "vacation_penalty_enabled": True,
    "vacation_penalty_duration_threshold": 8, # Not changed by tuner
    "vacation_penalty_spend_threshold": 165.56,
    "vacation_penalty_per_diem_pct": 0.69,
    "vacation_penalty_receipt_pct": 0.41,
    "extreme_day_receipt_threshold": 1755.56,
    "extreme_day_high_receipt_pct": 0.60,
    "extreme_day_low_receipt_multiplier": 0.57,
    "eff_slope": 0.30,
    "per_diem_floor_rate": 60.00, # Not changed by tuner
    "per_diem_floor_duration": 15, # Not changed by tuner
    "long_trip_duration_threshold": 9, # New tunable parameter
    
    # New parameters for the 3-tier receipt logic
    "receipt_low_tier_threshold": 316.67,
    "receipt_sweet_spot_lower_bound": 750.00,
    "receipt_sweet_spot_upper_bound": 800.00,
    "receipt_low_tier_pct": 0.10,
    "receipt_standard_pct": 0.3444,
    "receipt_sweet_spot_pct": 0.8111,
    "receipt_high_tier_diminishing_pct": 0.1889,
}

def clean_and_convert(val, target_type):
    """A robust function to clean and convert inputs to the correct numeric type."""
    if isinstance(val, (int, float)):
        return target_type(val)
    try:
        # Handle strings with potential non-numeric characters like '$' or ','
        s_val = str(val)
        # Extract a clean numeric string using regex
        numeric_part = re.search(r'[-+]?[\d,.]+', s_val)
        if numeric_part:
            clean_str = numeric_part.group(0).replace(',', '')
            return target_type(float(clean_str))
    except (ValueError, TypeError, AttributeError):
        # Return 0 if conversion fails, a safe default
        return target_type(0)
    # Fallback if no numeric part is found
    return target_type(0)

def round_legacy(x):
    rounded = round(x, 2)
    # The original bug is likely based on the string representation
    s_rounded = f"{rounded:.2f}"
    if s_rounded.endswith(".49") or s_rounded.endswith(".99"):
        # Use Decimal for precision addition to avoid float issues
        return float(Decimal(s_rounded) + Decimal("0.01"))
    return rounded

def get_per_diem_total(trip_duration_days, miles_traveled, total_receipts_amount, config):
    per_diem_rate = 100
    
    # This logic corresponds to the $177.91 baseline
    if trip_duration_days > 13:
        per_diem_rate = config["per_diem_rate_14_plus_days"]
    elif trip_duration_days >= 10:
        per_diem_rate = config["per_diem_rate_10_plus_days"]
    
    per_diem_total = trip_duration_days * per_diem_rate

    # Apply the per-diem floor for long trips
    floor_duration = config.get("per_diem_floor_duration", 15)
    if trip_duration_days >= floor_duration:
        floor_rate = config.get("per_diem_floor_rate", 60)
        per_diem_total = max(per_diem_total, trip_duration_days * floor_rate)

    return per_diem_total

def get_mileage_total(trip_duration_days, miles_traveled, config):
    primary_mileage_rate = 0.58
    
    # Tiered rates based on total mileage
    bp1 = config["mileage_breakpoint_1"]
    bp2 = config["mileage_breakpoint_2"]
    rate1 = config["mileage_rate_tier_1"]
    rate2 = config["mileage_rate_tier_2"]
    rate3 = config["mileage_rate_tier_3"]

    if miles_traveled > bp2:
        return (100 * primary_mileage_rate) + ((bp1 - 100) * rate1) + ((bp2 - bp1) * rate2) + ((miles_traveled - bp2) * rate3)
    elif miles_traveled > bp1:
        return (100 * primary_mileage_rate) + ((bp1 - 100) * rate1) + ((miles_traveled - bp1) * rate2)
    elif miles_traveled > 100:
        return (100 * primary_mileage_rate) + ((miles_traveled - 100) * rate1)
    
    return miles_traveled * primary_mileage_rate

def get_receipt_total(trip_duration_days, miles_traveled, total_receipts_amount, config):
    # This function is being refactored to implement a new 3-tier receipt logic
    # based on the "sweet spot" theory from the interviews.
    path = "TIERED_RECEIPT_LOGIC"
    
    # --- Configurable thresholds for the new logic ---
    low_receipt_threshold = config.get("receipt_low_tier_threshold", 200.0)
    sweet_spot_lower_bound = config.get("receipt_sweet_spot_lower_bound", 600.0)
    sweet_spot_upper_bound = config.get("receipt_sweet_spot_upper_bound", 800.0)
    
    # --- Configurable percentages for the tiers ---
    low_tier_pct = config.get("receipt_low_tier_pct", 0.1) # Penalized tier
    standard_pct = config.get("receipt_standard_pct", 0.5) # The "normal" rate
    sweet_spot_pct = config.get("receipt_sweet_spot_pct", 0.9) # High reimbursement rate
    high_tier_diminishing_pct = config.get("receipt_high_tier_diminishing_pct", 0.3) # Diminishing returns

    receipt_total = 0
    penalty = 0

    if total_receipts_amount < low_receipt_threshold:
        path += "_LOW_TIER_PENALTY"
        # Apply a simple low percentage for small amounts, plus the old penalty logic.
        receipt_total = total_receipts_amount * low_tier_pct
        penalty = -50 if 0 < total_receipts_amount <= 20 else 0

    elif low_receipt_threshold <= total_receipts_amount < sweet_spot_lower_bound:
        path += "_STANDARD_TIER"
        receipt_total = total_receipts_amount * standard_pct

    elif sweet_spot_lower_bound <= total_receipts_amount <= sweet_spot_upper_bound:
        path += "_SWEET_SPOT_TIER"
        # This tier gets the most favorable reimbursement rate
        receipt_total = total_receipts_amount * sweet_spot_pct

    else: # total_receipts_amount > sweet_spot_upper_bound
        path += "_HIGH_TIER_DIMINISHING"
        # Calculate reimbursement up to the sweet spot, then apply diminishing returns
        receipt_total = (sweet_spot_upper_bound * sweet_spot_pct) + \
                        ((total_receipts_amount - sweet_spot_upper_bound) * high_tier_diminishing_pct)

    # The existing logic for 1-day and 2-day high-receipt trips might still be valid
    # as separate, overriding rules. We will keep them for now.
    if trip_duration_days == 1 and total_receipts_amount > 500:
        upper_tier_threshold = config.get("one_day_upper_tier_threshold", 800)
        if total_receipts_amount > upper_tier_threshold:
            path = "ONE_DAY_HIGH_RECEIPT_UPPER_TIER"
            multiplier = config.get("one_day_upper_tier_multiplier", 0.6)
        else:
            path = "ONE_DAY_HIGH_RECEIPT_MULTIPLIER"
            multiplier = config.get("one_day_high_receipt_multiplier", 0.6)
        return total_receipts_amount * multiplier, 0, path

    if trip_duration_days == 2 and total_receipts_amount > 500:
        upper_tier_threshold = config.get("two_day_upper_tier_threshold", 800)
        if total_receipts_amount > upper_tier_threshold:
            path = "TWO_DAY_HIGH_RECEIPT_UPPER_TIER"
            multiplier = config.get("two_day_upper_tier_multiplier", 0.7)
        else:
            path = "TWO_DAY_HIGH_RECEIPT_MULTIPLIER"
            multiplier = config.get("two_day_high_receipt_multiplier", 0.7)
        return total_receipts_amount * multiplier, 0, path

    return receipt_total, penalty, path

def get_efficiency_bonus(trip_duration_days, miles_traveled, config):
    if trip_duration_days == 0:
        return 0
    
    mpd = miles_traveled / trip_duration_days
    
    if 150 <= mpd <= 250:
        return (mpd - 150) * config["eff_slope"]
    elif mpd < 100 or mpd > 300:
        return -50
    
    return 0

def calculate_reimbursement(trip_duration_days, miles_traveled, total_receipts_amount, debug=False, config=None):
    if config is None:
        config = DEFAULT_CONFIG.copy() # Ensure a consistent config object
    
    # --- Input Sanitization ---
    trip_duration_days = clean_and_convert(trip_duration_days, int)
    miles_traveled = clean_and_convert(miles_traveled, float)
    total_receipts_amount = clean_and_convert(total_receipts_amount, float)

    path = "NORMAL"
    receipt_path = None # Initialize receipt_path

    # Special case for extreme 1-day trips
    if trip_duration_days == 1 and miles_traveled > 800:
        if total_receipts_amount > config["extreme_day_receipt_threshold"]:
            path = "SPECIAL_EXTREME_ONE_DAY_HIGH_RECEIPT"
            computed_total = total_receipts_amount * config["extreme_day_high_receipt_pct"]
        else:
            path = "SPECIAL_EXTREME_ONE_DAY_LOW_RECEIPT"
            computed_total = (miles_traveled + total_receipts_amount) * config["extreme_day_low_receipt_multiplier"]
        
        if debug:
             return {
                "path": path, "receipt_path": None, "per_diem": 0, "mileage": 0, "receipts$": computed_total, "penalty": 0, "eff_bonus": 0,
                "grand": round_legacy(computed_total)
            }
        return round_legacy(computed_total)

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
        mileage_total = get_mileage_total(trip_duration_days, miles_traveled, config)
        
        # Apply a simple, harsh penalty directly to the main components
        final_per_diem = per_diem_total * config.get("vacation_penalty_per_diem_pct", 0.5)
        final_receipts = total_receipts_amount * config.get("vacation_penalty_receipt_pct", 0.5) # Use raw receipts
        
        efficiency_bonus = get_efficiency_bonus(trip_duration_days, miles_traveled, config)
        computed_total = final_per_diem + mileage_total + final_receipts + efficiency_bonus
        
        if debug:
            return {
                "path": path, "receipt_path": "N/A", "miles_per_day": miles_traveled / trip_duration_days if trip_duration_days > 0 else 0,
                "per_diem": final_per_diem, "mileage": mileage_total, 
                "receipts$": final_receipts, "penalty": 0, "eff_bonus": efficiency_bonus, "grand": round_legacy(computed_total)
            }
        return round_legacy(computed_total)
        
    # --- New Two-Tier Logic for Long Trips ---
    if trip_duration_days >= config["long_trip_duration_threshold"]:
        path = "LONG_TRIP_TWO_TIER"
        receipt_path = "LONG_TRIP_SWEET_SPOT_TIERS"
        
        per_diem_total = trip_duration_days * config["per_diem_rate_long_trip"]
        mileage_total = get_mileage_total(trip_duration_days, miles_traveled, config)
        efficiency_bonus = get_efficiency_bonus(trip_duration_days, miles_traveled, config)

        # Apply daily spending caps first
        cap_per_day = (
            config["receipt_cap_long_trip_high"]
            if (total_receipts_amount / trip_duration_days) > config["high_spend_threshold"]
            else config["receipt_cap_long_trip_low"]
        )
        reimbursable = min(total_receipts_amount, cap_per_day * trip_duration_days)

        # Now apply the piece-wise "sweet spot" logic
        low_tier_ceiling = 600
        sweet_spot_upper = config.get("receipt_sweet_spot_upper_bound", 800)
        sweet_spot_pct = config.get("receipt_sweet_spot_pct", 0.9)
        pct_low_tier = 0.80
        pct_high_tier = 0.50

        if reimbursable > sweet_spot_upper:
            receipt_total = (low_tier_ceiling * pct_low_tier) + \
                            ((sweet_spot_upper - low_tier_ceiling) * sweet_spot_pct) + \
                            ((reimbursable - sweet_spot_upper) * pct_high_tier)
        elif reimbursable > low_tier_ceiling:
            receipt_total = (low_tier_ceiling * pct_low_tier) + \
                            ((reimbursable - low_tier_ceiling) * sweet_spot_pct)
        else:
            receipt_total = reimbursable * pct_low_tier

        computed_total = per_diem_total + mileage_total + receipt_total + efficiency_bonus
        
        # This path should be self-contained and not call get_receipt_total
        if debug:
            miles_per_day = miles_traveled / trip_duration_days if trip_duration_days > 0 else 0
            return {
                "path": path, "receipt_path": receipt_path, "miles_per_day": miles_per_day,
                "per_diem": per_diem_total, "mileage": mileage_total, 
                "receipts$": receipt_total, "penalty": 0, "eff_bonus": efficiency_bonus, "grand": round_legacy(computed_total)
            }
        return round_legacy(computed_total)
    
    # --- Standard Calculation Logic ---
    per_diem_total = get_per_diem_total(trip_duration_days, miles_traveled, total_receipts_amount, config)
    mileage_total = get_mileage_total(trip_duration_days, miles_traveled, config)
    receipt_total, penalty, receipt_path = get_receipt_total(trip_duration_days, miles_traveled, total_receipts_amount, config)
    efficiency_bonus = get_efficiency_bonus(trip_duration_days, miles_traveled, config)

    computed_total = per_diem_total + mileage_total + receipt_total + penalty + efficiency_bonus
    computed_total = round_legacy(computed_total)

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
        # Pass raw strings to the calculation function, which handles sanitization
        trip_duration_days = sys.argv[1]
        miles_traveled = sys.argv[2]
        total_receipts_amount = sys.argv[3]
        
        reimbursement = calculate_reimbursement(
            trip_duration_days,
            miles_traveled,
            total_receipts_amount,
            config=DEFAULT_CONFIG
        )
        # Ensure output is formatted to exactly two decimal places
        print(f"{reimbursement:.2f}")
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