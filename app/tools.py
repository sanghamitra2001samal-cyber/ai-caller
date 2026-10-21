import json
import os

# Load states once
STATES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'content', 'approved_states.json')

def get_approved_states():
    try:
        with open(STATES_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading states: {e}")
        return []

APPROVED_STATES = get_approved_states()

def is_valid_state(state_code: str) -> bool:
    """
    Checks if the provided state code (2 letters) is in the approved list.
    """
    if not state_code:
        return False
    return state_code.upper() in APPROVED_STATES

def validate_debt_amount(amount: int) -> bool:
    """
    Checks if debt is >= 10,000
    """
    return amount >= 10000
