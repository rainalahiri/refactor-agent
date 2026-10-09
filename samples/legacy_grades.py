# grade calculator - written in a hurry for fall semester
def calc(students):
    result = []
    for s in students:
        total = 0
        for i in range(len(s[1])):
            total = total + s[1][i]
        if len(s[1]) > 0:
            avg = total / len(s[1])
        else:
            avg = 0
        if avg >= 90:
            g = "A"
        else:
            if avg >= 80:
                g = "B"
            else:
                if avg >= 70:
                    g = "C"
                else:
                    if avg >= 60:
                        g = "D"
                    else:
                        g = "F"
        result.append(s[0] + ": " + str(round(avg, 1)) + " (" + g + ")")
    return result


def honor_roll(students):
    names = []
    for s in students:
        total = 0
        for i in range(len(s[1])):
            total = total + s[1][i]
        if len(s[1]) > 0 and total / len(s[1]) >= 90:
            names.append(s[0])
    return names