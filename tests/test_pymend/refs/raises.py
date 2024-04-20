"""_summary_."""

def raises():
    """_summary_.

    Raises
    ------
    ValueError
        _description_
    TypeError
        _description_
    SpecificError
        _description_
    """
    my_exceptions = [ValueError, TypeError]
    raise ValueError
    raise KeyError
    raise TypeError(msg)
    raise ValueError
    raise
    raise my_exceptions[0]