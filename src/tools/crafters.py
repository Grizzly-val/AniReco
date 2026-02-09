def craft_key(params: dict):
    key = ""
    for k, v in params.items():
        key += f"{str(k)}:{str(v)}|"
    return key