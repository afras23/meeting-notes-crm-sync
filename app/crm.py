def push_to_crm(payload: dict):
    return {
        "status": "queued",
        "changes_detected": list(payload.keys())
    }
