def clean_dict(d):
    for key, value in d.items():
        if isinstance(value, list):
            clean_list(value)
        elif isinstance(value, dict):
            clean_dict(value)
        else:
            # newvalue = value.strip()
            if hasattr(key, 'strip'):
                d.pop(key)
                d[key.strip()] = hasattr(value, 'strip') and value.strip() or value

def clean_list(l):
    for index, item in enumerate(l):
        if isinstance(item, dict):
            clean_dict(item)
        elif isinstance(item, list):
            clean_list(item)
        else:
            l[index] = hasattr(item, 'strip') and item.strip() or item
