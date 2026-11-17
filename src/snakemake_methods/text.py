"""Small text helpers for methods prose"""


def join(items, last=" and "):
    """'a, b and c'"""
    items = [str(x) for x in items]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + last + items[-1]


def number(value):
    """Thousands separators for integers (10,000)"""
    return (
        f"{value:,}"
        if isinstance(value, int) and not isinstance(value, bool)
        else str(value)
    )


def percent(value, digits=0):
    """0.5 -> '50%'"""
    return f"{value:.{digits}%}"


def code(value):
    """Inline code"""
    return f"`{value}`"
