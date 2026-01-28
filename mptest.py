"""
/***************************************************************************
 SimstockQGIS
        copyright            : (C) 2023-2026 by UCL
        email                : shyam.amrith.14@ucl.ac.uk
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import multiprocessing as mp
import os
import platform
import subprocess
import argparse
import json
import pandas as pd
import sys

# Add psutil location to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "eppy-scripts"))
try:
    import psutil as pu
except:
    pass

parser = argparse.ArgumentParser()
parser.add_argument("cwd", help="The path to the user cwd")
parser.add_argument("--singlecore", action="store_true", help="If specified, simulation will use single core")
args = parser.parse_args()

class EP_Run():
    def __init__(self, cwd):
        self.plugin_dir = os.path.dirname(__file__)
        self.EP_DIR = os.path.join(self.plugin_dir, "EnergyPlus")
        self.cwd = cwd
        self.idf_dir = os.path.join(cwd, "idf_files")
        self.preprocessed_df = pd.read_csv(os.path.join(self.plugin_dir, "sa_preprocessed.csv"))
        self.idf_files = [os.path.join(self.idf_dir, f"{bi}.idf") for bi in self.preprocessed_df[self.preprocessed_df["shading"]==False]["bi"].unique()]

        # Load config file
        with open(os.path.join(self.plugin_dir, "config.json"), "r") as read_file:
            self.config = json.load(read_file)
        self.epw_file = os.path.join(self.cwd, self.config["epw"])
        
        # Find the computer's operating system and find energyplus version
        system = platform.system().lower()
        if system in ['windows', 'linux', 'darwin']:
            self.energyplusexe = os.path.join(self.EP_DIR, 'ep8.9_{}/energyplus'.format(system))
            self.readvarseso   = os.path.join(self.EP_DIR, 'ep8.9_{}/ReadVarsESO'.format(system))


    def run_ep(self, idf_file):
        output_dir = idf_file[:-4]
        output_path = os.path.join(self.idf_dir, output_dir)

        # Delete existing results csv
        if os.path.exists(os.path.join(output_path, "eplusout.csv")):
            os.remove(os.path.join(output_path, "eplusout.csv"))

        # Run the EnergyPlus simulation
        out = subprocess.run([self.energyplusexe, '-d', output_dir, '-w', self.epw_file, idf_file],
                             cwd = self.idf_dir, capture_output=True, text=True) #no readvarseso
        if out.returncode != 0:
            return os.path.join(output_path, 'eplusout.err')
            #raise RuntimeError(f"EnergyPlus simulation of {output_dir} failed.\n"
            #                   f"Check the EnergyPlus err file '{os.path.join(output_path, 'eplusout.err')}'")
        
        # Generate the .rvi file
        self.generate_rvi(output_path)
        
        # Call ReadVarsESO to produce the results csv
        self.run_readvarseso(output_path)


    @staticmethod
    def generate_rvi(output_path):
        with open (os.path.join(output_path, "results-rvi.rvi"), "w") as f:
            f.write("eplusout.eso\neplusout.csv\n0")


    def run_readvarseso(self, output_path):
        subprocess.run([self.readvarseso, "results-rvi.rvi", "unlimited"], cwd=output_path)


    def run_ep_multi(self, cores):
        p = mp.Pool(cores)
        errs = p.map(self.run_ep, self.idf_files)
        p.close()
        return errs


    def run_ep_single(self):
        errs = []
        for i, idf_file in enumerate(self.idf_files):
            print(f"Starting simulation {i+1} of {len(self.idf_files)}")
            errs.append(self.run_ep(idf_file))
        return errs



def main():
    cwd = args.cwd
    runner = EP_Run(cwd)

    # Single-core simulation
    if args.singlecore:
        errs = runner.run_ep_single()
    
    # Multi-core simulation
    else:
        try:
            cores = pu.cpu_count(logical=False) - 1 #use one less core than available
        except:
            cores = mp.cpu_count() - 1
        errs = runner.run_ep_multi(cores)

    errs = [e for e in errs if e is not None]


if __name__ == '__main__':
    main()
