# legacy inventory module - do not touch, it works (mostly)
inv = {}  # global state

def do_stuff(action, name, qty=0, price=0):
    global inv
    if action == "add":
        if name in inv:
            inv[name][0] = inv[name][0] + qty
        else:
            inv[name] = [qty, price]
    elif action == "remove":
        if name in inv:
            inv[name][0] = inv[name][0] - qty
            if inv[name][0] <= 0:
                del inv[name]
    elif action == "total":
        t = 0
        for k in inv:
            t = t + inv[k][0] * inv[k][1]
        return t
    elif action == "report":
        s = ""
        for k in inv:
            s = s + k + ": " + str(inv[k][0]) + " @ $" + str(inv[k][1]) + "\n"
        return s