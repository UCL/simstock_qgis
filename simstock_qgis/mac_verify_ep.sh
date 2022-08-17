#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
xattr -d com.apple.quarantine "$SCRIPT_DIR/EnergyPlus/ep8.9_darwin/energyplus"
xattr -d com.apple.quarantine "$SCRIPT_DIR/EnergyPlus/ep8.9_darwin/libenergyplusapi.8.9.0.dylib"
xattr -d com.apple.quarantine "$SCRIPT_DIR/EnergyPlus/ep8.9_darwin/ReadVarsESO"
xattr -d com.apple.quarantine "$SCRIPT_DIR/EnergyPlus/ep8.9_darwin/libgfortran.3.dylib"
xattr -d com.apple.quarantine "$SCRIPT_DIR/EnergyPlus/ep8.9_darwin/libgcc_s.1.dylib"
xattr -d com.apple.quarantine "$SCRIPT_DIR/EnergyPlus/ep8.9_darwin/libgcc_s.1.dylib"
xattr -d com.apple.quarantine "$SCRIPT_DIR/EnergyPlus/ep8.9_darwin/libquadmath.0.dylib"
