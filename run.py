import sys
from solution import calculate_reimbursement, DEFAULT_CONFIG

# --- Self-Contained Solution for Black Box Challenge ---

# This script contains all necessary logic to run independently.

# --- Configuration (from our best run) ---
DEFAULT_CONFIG = {
    "per_diem_rate_10_plus_days": 70,
    "per_diem_rate_14_plus_days": 55,
    "mileage_rate_tier_1": 0.45,
    "mileage_rate_tier_2": 0.40,
    "mileage_rate_tier_3": 0.4,
    "mileage_breakpoint_1": 650.0,
    "mileage_breakpoint_2": 800,
    "receipt_cap_4_6_days": 250,
    "high_cost_receipt_percentage": 0.25,
    "short_trip_high_receipt_pct": 0.5,
    "one_day_high_receipt_multiplier": 0.5,
    "one_day_upper_tier_threshold": 800,
    "one_day_upper_tier_multiplier": 0.6,
    "two_day_high_receipt_multiplier": 0.5,
    "two_day_upper_tier_threshold": 800,
    "two_day_upper_tier_multiplier": 0.7,
    "receipt_tier_1_threshold": 900.0,
    "receipt_tier_1_percentage": 0.6,
    "receipt_tier_2_percentage": 0.2,
    "standard_receipt_pct": 0.4,
    "standard_receipt_pct_1_3_days": 0.55,
    "standard_receipt_pct_4_6_days": 0.6000000000000001,
    "per_diem_rate_long_trip": 50,
    "receipt_cap_long_trip_low": 120.0,
    "receipt_cap_long_trip_high": 130.0,
    "high_spend_threshold": 140.0,
    "receipt_sweet_spot_upper_bound": 850.0,
    "receipt_sweet_spot_pct": 0.95,
    "vacation_penalty_enabled": True,
    "vacation_penalty_duration_threshold": 8,
    "vacation_penalty_spend_threshold": 150.0,
    "vacation_penalty_per_diem_pct": 0.6499999999999999,
    "vacation_penalty_receipt_pct": 0.44999999999999996,
    "extreme_day_receipt_threshold": 1600.0,
    "extreme_day_high_receipt_pct": 0.5,
    "extreme_day_low_receipt_multiplier": 0.6,
    "eff_slope": 0.4,
    "per_diem_floor_rate": 60,
    "per_diem_floor_duration": 15,
}

# --- Helper Functions ---

def clean_and_convert(val, target_type):
    if isinstance(val, (int, float)):
        return target_type(val)
    try:
        s_val = str(val)
        numeric_part = re.search(r'[-+]?[\d,.]+', s_val)
        if numeric_part:
            clean_str = numeric_part.group(0).replace(',', '')
            return target_type(float(clean_str))
    except (ValueError, TypeError, AttributeError):
        return target_type(0)
    return target_type(0)

def round_legacy(x):
    rounded = round(x, 2)
    s_rounded = f"{rounded:.2f}"
    if s_rounded.endswith(".49") or s_rounded.endswith(".99"):
        return float(Decimal(s_rounded) + Decimal("0.01"))
    return rounded

def get_per_diem_total(trip_duration_days, miles_traveled, total_receipts_amount, config):
    per_diem_rate = 100
    if trip_duration_days > 13:
        per_diem_rate = config["per_diem_rate_14_plus_days"]
    elif trip_duration_days >= 10:
        per_diem_rate = config["per_diem_rate_10_plus_days"]
    per_diem_total = trip_duration_days * per_diem_rate
    floor_duration = config.get("per_diem_floor_duration", 15)
    if trip_duration_days >= floor_duration:
        floor_rate = config.get("per_diem_floor_rate", 60)
        per_diem_total = max(per_diem_total, trip_duration_days * floor_rate)
    return per_diem_total

def get_mileage_total(trip_duration_days, miles_traveled, config):
    primary_mileage_rate = 0.58
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
    path = "STANDARD"
    is_short_expensive_trip = (trip_duration_days <= 4 and total_receipts_amount > 1000)
    if is_short_expensive_trip:
        percentage = config.get("short_trip_high_receipt_pct", 0.5)
        path = "SHORT_TRIP_HIGH_RECEIPT_BONUS"
        return total_receipts_amount * percentage, 0, path
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
    daily_spending_limit = 0
    if 1 <= trip_duration_days <= 3: daily_spending_limit = 75
    elif 4 <= trip_duration_days <= 6: daily_spending_limit = config["receipt_cap_4_6_days"]
    reimbursable_receipts = total_receipts_amount
    if trip_duration_days > 0 and daily_spending_limit > 0:
        daily_spending = total_receipts_amount / trip_duration_days
        if daily_spending > daily_spending_limit:
            path = "DAILY_SPENDING_LIMIT_APPLIED"
            reimbursable_receipts = daily_spending_limit * trip_duration_days
    tier_1_threshold = config.get("receipt_tier_1_threshold", 820)
    tier_1_pct = config.get("receipt_tier_1_percentage", 0.6)
    tier_2_pct = config.get("receipt_tier_2_percentage", 0.28)
    if 1 <= trip_duration_days <= 3: standard_pct = config.get("standard_receipt_pct_1_3_days", 0.55)
    elif 4 <= trip_duration_days <= 6: standard_pct = config.get("standard_receipt_pct_4_6_days", 0.6)
    else: standard_pct = config.get("standard_receipt_pct", 0.55)
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

def get_efficiency_bonus(trip_duration_days, miles_traveled, config):
    if trip_duration_days == 0: return 0
    mpd = miles_traveled / trip_duration_days
    if 150 <= mpd <= 250: return (mpd - 150) * config["eff_slope"]
    elif mpd < 100 or mpd > 300: return -50
    return 0

# --- Main Execution ---

def main():
    """
    This script serves as the command-line entry point for the reimbursement calculation.
    It takes three arguments, calculates the reimbursement, and prints the result.
    """
    if len(sys.argv) != 4:
        print("Usage: python run.py <trip_duration_days> <miles_traveled> <total_receipts_amount>", file=sys.stderr)
        sys.exit(1)

    # Pass raw string arguments directly to the calculation function.
    # The robust sanitization logic is inside calculate_reimbursement.
    trip_duration_days = sys.argv[1]
    miles_traveled = sys.argv[2]
    total_receipts_amount = sys.argv[3]

    reimbursement = calculate_reimbursement(
        trip_duration_days=trip_duration_days,
        miles_traveled=miles_traveled,
        total_receipts_amount=total_receipts_amount,
        config=DEFAULT_CONFIG
    )

    print(f"{reimbursement:.2f}")

if __name__ == "__main__":
    main() 