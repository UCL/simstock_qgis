import tarfile
import os

def main():
    EP_dir = os.path.join(os.path.dirname(__file__), "EnergyPlus")
    fpath = os.path.join(EP_dir, "EnergyPlus-8.9.0-40101eaafd-Darwin-x86_64.tar.gz")

    with tarfile.open(fpath, "r:gz") as tar:
        tar.extractall(EP_dir)

if __name__ == "__main__":
    main()