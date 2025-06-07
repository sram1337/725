#!/bin/bash

# This is your submission script.
# It should be a self-contained script that takes three arguments:
# 1. trip_duration_days (integer)
# 2. miles_traveled (integer)
# 3. total_receipts_amount (float)
#
# The script should output a single number: the calculated reimbursement amount.

# Example:
# ./run.sh 5 250 150.75
# Should output something like: 487.25

# --- Your implementation below ---

python3 solution.py "$1" "$2" "$3" 