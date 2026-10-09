# reads key=value config text
def parse(text, defaults={}):
    cfg = defaults
    for line in text.split("\n"):
        line = line.strip()
        if line == "" or line[0] == "#":
            continue
        try:
            k = line.split("=")[0].strip()
            v = line.split("=")[1].strip()
        except:
            continue
        if v.lower() == "true":
            v = True
        elif v.lower() == "false":
            v = False
        else:
            try:
                v = int(v)
            except:
                pass
        cfg[k] = v
    return cfg