TOOLS = [
    {
        "type": "function",
        "name": "check_state_validity",
        "description": "Checks if the user's US state is in the approved list for the program.",
        "parameters": {
            "type": "object",
            "properties": {
                "state_code": {
                    "type": "string",
                    "description": "The 2-letter state code (e.g. CA, NY, TX)."
                }
            },
            "required": ["state_code"]
        }
    },
    {
        "type": "function",
        "name": "check_debt_qualification",
        "description": "Checks if the debt amount meets the minimum requirement of $10,000.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "integer",
                    "description": "The total unsecured debt amount in USD."
                }
            },
            "required": ["amount"]
        }
    },
    {
        "type": "function",
        "name": "transfer_call",
        "description": "Initiates a warm transfer to the specialist when the user is fully qualified.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Reason for transfer (e.g. 'Qualified')."
                }
            },
            "required": ["reason"]
        }
    }
]
