def token_color(token):
    """מחזיר את צבע הכלי ('w'/'b') או None אם התא ריק."""
    if token == ".":
        return None
    return token[0]

def token_type(token):
    """מחזיר את סוג הכלי ('K','Q','R','B','N','P') או None אם התא ריק."""
    if token == ".":
        return None
    return token[1]