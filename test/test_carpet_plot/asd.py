import itertools

a = itertools.count()
b = itertools.cycle([3, 4, 5])

for i in range(6):
    print(next(b))
