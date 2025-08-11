import re
import os

name_regex = r'^[a-zA-Z0-9._-]+$'
number_regex = r'^[0-9]+$'

def validate_string(string: str, validator: dict)-> str:
    required = validator.get("required")
    length = validator.get("length")
    name = validator.get("name")
    number = validator.get("number")
    
    if required and (not string or len(string) == 0):
        return required
    if (length and length.get("value") and length.get("message")):
        le = length.get("value")
        if (len(string) < le):
            return length.get("message")
    if (name and not re.match(name_regex, string)):
        return name
    if (number and not re.match(number_regex, string)):
        return number
    return ""

def validate_file(file, allowed_extensions: list):
    ext = os.path.splitext(file.name)[1]
    if ext not in allowed_extensions:
        return False
    return True
