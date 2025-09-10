import requests
import os

def main():
    help = os.environ['GHBKP_TOKEN']
    help_bin = help.encode('utf-8')
    out_path = os.environ['OUT_PATH']

    with open(out_path + "test.txt", "wb") as f:
        f.write(help_bin)

    pass

if __name__ == "__main__":
    main()

