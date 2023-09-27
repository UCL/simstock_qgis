"""
/***************************************************************************
 SimstockQGIS
        copyright            : (C) 2023 by UCL
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

import tarfile
import os

def main():
    EP_dir = os.path.join(os.path.dirname(__file__), "EnergyPlus")
    fpath = os.path.join(EP_dir, "EnergyPlus-8.9.0-40101eaafd-Darwin-x86_64.tar.gz")

    with tarfile.open(fpath, "r:gz") as tar:
        tar.extractall(EP_dir)

if __name__ == "__main__":
    main()