def calculatedTimeout(retry_count: int) -> int:
    '''Uses progressive timeout strategy:
    - Attempt 1: 120 * 1000 seconds (2 minutes)
    - Attempt 2: 180 * 1000 seconds (3 minutes)
    - Attempt 3: 300 * 1000 seconds (5 minutes)
    - Attempt 4: 420 * 1000 seconds (7 minutes)'''

    # Progressive timeout based on retry attempt
    timeout_map = {
        0: 120*1000,  # First attempt: 2 minutes
        1: 180*1000,  # Second attempt: 3 minutes
        2: 300*1000,  # Third attempt: 5 minutes
        3: 420*1000   # Fourth attempt: 7 minutes
    }
    # default to 300 if not found
    timeout = timeout_map.get(retry_count, 300 * 1000)
    return timeout
