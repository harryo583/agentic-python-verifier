import sys
assert 0 <= counter <= 10, 'Precondition failed: 0 <= counter <= 10'
assert 0 <= counter <= 10, 'Invariant failed: 0 <= counter <= 10'
def increment(counter):
    if counter < 10:
        return counter + 1
    else:
        return 10