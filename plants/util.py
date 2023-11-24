def htime(human_form):
    unit = human_form[-1]
    multipliers = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
        "w": 7 * 86400,
        "M": 31 * 86400,
        "Y": 365 * 86400,
    }

    if unit in multipliers:
        return int(human_form[:-1]) * multipliers[unit]
    return int(human_form)
