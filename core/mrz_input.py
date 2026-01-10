from mrz.checker.td1 import TD1CodeChecker
from mrz.checker.td2 import TD2CodeChecker
from mrz.checker.td3 import TD3CodeChecker

def get_id_data(input_string):
    fields = None
    if len(input_string)==90:
        split_input = [input_string[i:i+30] + ("\n" if i+30 < len(input_string) else "") for i in range(0, len(input_string), 30)]
        td_check = TD1CodeChecker("".join(split_input))
        fields = td_check.fields()
    elif len(input_string)==72:
        split_input = [input_string[i:i+36] + ("\n" if i+36 < len(input_string) else "") for i in range(0, len(input_string), 36)]
        td_check = TD2CodeChecker("".join(split_input))
        fields = td_check.fields()
    elif len(input_string)==88:
        split_input = [input_string[i:i+44] + ("\n" if i+44 < len(input_string) else "") for i in range(0, len(input_string), 44)]
        td_check = TD2CodeChecker("".join(split_input))
        fields = td_check.fields()

    return fields