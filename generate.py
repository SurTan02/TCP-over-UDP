# generate txt file with number 1 to 1<<12

with open('files/numbers.txt', 'w') as f:
    for i in range((1 << 12) * 7):
        f.write(str(i) + '\n')
