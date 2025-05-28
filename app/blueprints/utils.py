def html_format_error_string(message: str, error: Exception = None, join: str = ": "):
    """
    Formats an error message string for HTML display by replacing newlines with HTML line breaks.
    Args:
        message (str): The main error message. This should not end with a colon if an error is provided.
        error (Exception, optional): The error to append to the main message. Defaults to None.
        join (str, optional): The string to join the message and error with. Defaults to ": ".
    Returns:
        str: The formatted error message with HTML line breaks.
    """

    error = str(error)

    output = f"{message}{join}{error}" if error else message
    output = error.replace("\n", "<br>")
    return output
