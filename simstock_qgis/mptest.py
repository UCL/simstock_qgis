import multiprocessing as mp
#import numpy as np
#import time
import os
import platform
import subprocess

class EP_Run():
    def __init__(self):
        self.plugin_dir = os.path.dirname(__file__)
        self.EP_DIR = os.path.join(self.plugin_dir, "EnergyPlus")
        self.idf_dir = os.path.join(self.plugin_dir, "idf_files")
        self.epw_file = os.path.join(self.plugin_dir, "GBR_ENG_London.Wea.Ctr-St.James.Park.037700_TMYx.2007-2021.epw")
        files = os.scandir(os.path.abspath(self.idf_dir))
        self.idf_files = [file.path for file in files if file.name[-4:] == ".idf"]
        
        # Find the computer's operating system and find energyplus version
        system = platform.system().lower()
        if system in ['windows', 'linux', 'darwin']:
            self.energyplusexe = os.path.join(self.EP_DIR, 'ep8.9_{}/energyplus'.format(system))
        
    def run_ep(self, idf_file):
        output_dir = idf_file[:-4]
        subprocess.run([self.energyplusexe, '-r','-d', output_dir, '-w', self.epw_file, idf_file])
        
    def run_ep_multi(self, cores):
        p = mp.Pool(cores)
        p.map(self.run_ep, self.idf_files)
        p.close()
    
def main():

    #multisquare(cores)
    runner = EP_Run()
    runner.run_ep_multi(8)

if __name__ == '__main__':
    main()