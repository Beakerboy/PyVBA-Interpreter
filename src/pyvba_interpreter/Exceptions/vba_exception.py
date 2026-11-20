class VbaException(Exception):
    msg: str
    # project, file, line, column, token
    context: tuple
