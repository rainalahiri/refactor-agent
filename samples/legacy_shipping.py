# shipping cost calculator
def ship(w, dist, express, intl, member):
    if intl:
        c = 15 + w * 2.5 + dist * 0.05
        if express:
            c = c * 2
    else:
        c = 5 + w * 1.2 + dist * 0.02
        if express:
            c = c + 10
    if member:
        if c > 50:
            c = c - c * 0.15
        else:
            c = c - c * 0.1
    if w > 30:
        c = c + 20
    return round(c, 2)