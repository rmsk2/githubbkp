import requests

def main():
    help = "this is a test"
    help_bin = help.encode('utf-8')

    with open("/data/test.txt", "wb") as f:
        f.write(help_bin)

    pass

if __name__ == "__main__":
    main()

