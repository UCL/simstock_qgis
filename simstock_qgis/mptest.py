import multiprocessing as mp
#import numpy as np
#import time
import os
import platform
import subprocess
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("idf_dir", help="The path to the idf files")
args = parser.parse_args()

class EP_Run():
    def __init__(self, idf_dir):
        self.plugin_dir = os.path.dirname(__file__)
        self.EP_DIR = os.path.join(self.plugin_dir, "EnergyPlus")
        self.idf_dir = idf_dir
        self.epw_file = os.path.join(self.plugin_dir, "GBR_ENG_London.Wea.Ctr-St.James.Park.037700_TMYx.2007-2021.epw")
        files = os.scandir(self.idf_dir)
        self.idf_files = [file.name for file in files if file.name[-4:] == ".idf"]
        
        # Find the computer's operating system and find energyplus version
        system = platform.system().lower()
        if system in ['windows', 'linux', 'darwin']:
            self.energyplusexe = os.path.join(self.EP_DIR, 'ep8.9_{}/energyplus'.format(system))
        
    def run_ep(self, idf_file):
        output_dir = idf_file[:-4]
        #subprocess.run([self.energyplusexe, '-r','-d', output_dir, '-w', self.epw_file, idf_file])
        out = subprocess.run([self.energyplusexe, '-d', output_dir, '-w', self.epw_file, idf_file], cwd = self.idf_dir, capture_output=True, text=True) #no readvarseso
        if out.returncode == 1:
            raise RuntimeError(out.stderr)
        
    def run_ep_multi(self, cores):
        p = mp.Pool(cores)
        p.map(self.run_ep, self.idf_files)
        p.close()
    
def main():

    idf_dir = args.idf_dir
    runner = EP_Run(idf_dir)
    cores = mp.cpu_count() - 1 #use one less core than available
    runner.run_ep_multi(cores)

if __name__ == '__main__':
    main()