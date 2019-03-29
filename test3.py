import os



for root, dirs, files in os.walk(r'.\flags', topdown=False):
    for name in dirs:
        print(f'num: {name}')
