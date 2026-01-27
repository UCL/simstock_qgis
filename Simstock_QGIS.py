# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SimstockQGIS
        begin                : 2022-05-17
        git sha              : $Format:%H$
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
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QVariant, QUrl
from qgis.PyQt.QtGui import QIcon, QDesktopServices
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QInputDialog, QWidget

from qgis.core import QgsProject, QgsVectorDataProvider, QgsVectorLayer, QgsField, QgsFields, QgsVectorFileWriter, QgsCoordinateTransformContext, QgsApplication

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .Simstock_QGIS_dialog import SimstockQGISDialog
import os

# My imports
import subprocess
import platform
import sys
import qgis.utils
from qgis.core import Qgis
from qgis.core import NULL as qgis_null
import time
import shutil
import numpy as np
import json
from zipfile import ZipFile
import logging
from logging.handlers import RotatingFileHandler
import warnings
from functools import reduce

# Pandas can cause problems in certain versions of QGIS
# This clause allows the plugin to be installed
# Import will be checked again in the initial setup routines
try:
    import pandas as pd
except:
    pass


class SimstockQGIS:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        self.iface.actionShowPythonDialog().trigger() #show console upon launch
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'SimstockQGIS_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Simstock QGIS')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
        
        # Custom additions
        self.custom_initialisation()


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('SimstockQGIS', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            # Add plugin to plugins dropdown
            self.iface.addPluginToMenu(
                self.menu,
                action)
            
            # Add plugin to Vector menu
            #self.iface.addPluginToVectorMenu(
            #    self.menu,
            #    action)

        self.actions.append(action)

        return action


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        # Default action
        icon_path = ':/plugins/Simstock_QGIS/icon.svg'
        self.add_action(
            icon_path,
            text=self.tr(u'Simstock'),
            callback=self.run,
            parent=self.iface.mainWindow())
        # Run "pyrcc5 -o resources.py resources.qrc" to update icon

        # Side action
        #self.add_action(
        #    icon_path,
        #    text=self.tr(u'Side action'),
        #    callback=self.side_action,
        #    parent=self.iface.mainWindow(),
        #    add_to_toolbar=False)
        
        # Help action
        self.help_action = QAction(QgsApplication.getThemeIcon("/mActionContextHelp.png"),
                                   self.tr("Simstock Documentation"),
                                   self.iface.mainWindow())
        # Add the action to the Help menu
        self.iface.pluginHelpMenu().addAction(self.help_action)
        self.help_action.triggered.connect(self.show_help)

        # will be set False in run()
        self.first_start = True

    
    #def side_action(self):
    #    print("side action")
    

    def show_help(self):
        """Display documentation online"""
        QDesktopServices.openUrl(QUrl('https://simstock.readthedocs.io/en/latest/simstockqgis.html'))
        # TODO: add link to plugin UI too


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Simstock QGIS'),
                action)
            self.iface.removeToolBarIcon(action)



##################################### CUSTOM CODE ##################################################
    def custom_initialisation(self):
        ### CUSTOM ADDITIONS
        # Update path to access Simstock scripts
        sys.path.insert(0, self.plugin_dir)

        # Initialise log
        logfile = os.path.join(self.plugin_dir, "log.log")
        logging.basicConfig(handlers=[RotatingFileHandler(logfile, maxBytes=100*1024*1024, backupCount=2)],
                            format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s - %(funcName)s - %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S",
                            level=logging.INFO)
        
        # Supress Eppy warnings which can confuse the user that something has gone wrong
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        warnings.filterwarnings("ignore", category=ResourceWarning)
        
        # Various check trackers
        self.initial_setup_worked = None #check if initial setup worked
        self.cwd_set = False #check if the user set the cwd
        
        # Startup E+ stuff
        self.EP_DIR = os.path.join(self.plugin_dir, "EnergyPlus")

        # Find the computer's operating system and find energyplus version
        self.system = platform.system().lower()
        if self.system in ['windows', 'linux', 'darwin']:
            self.energyplusexe = os.path.join(self.EP_DIR, 'ep8.9_{}/energyplus'.format(self.system))
            self.readvarseso = os.path.join(self.EP_DIR, 'ep8.9_{}/ReadVarsESO'.format(self.system))
        
        # Locate QGIS Python, differs by OS
        qgis_python_dir = sys.exec_prefix
        if self.system == "windows":
            self.qgis_python_location = os.path.join(qgis_python_dir, "python")
        if self.system == "darwin":
            self.qgis_python_location = os.path.join(qgis_python_dir, "bin", "python3")

        # Update paths to pre-included packages
        self.scripts_dir = os.path.join(self.plugin_dir, "eppy-scripts")
        # Use eppy 5.56 if Python version <= 3.9 else use eppy 5.63
        if sys.version_info.minor <= 9:
            eppy_dir = os.path.join(self.scripts_dir, "eppy556")
        else:
            eppy_dir = os.path.join(self.scripts_dir, "eppy563")
        munch_dir = os.path.join(self.scripts_dir, "munch250")
        decorator_dir = os.path.join(self.scripts_dir, "decorator511")

        # Add these to Python path
        sys.path.append(eppy_dir)
        sys.path.append(munch_dir)
        sys.path.append(decorator_dir)

        # Set up Eppy
        from eppy.modeleditor import IDF, IDDAlreadySetError
        if self.system in ['windows', 'linux', 'darwin']:
            iddfile = os.path.join(self.EP_DIR, 'ep8.9_{}/Energy+.idd'.format(self.system))
        try:
            IDF.setiddname(iddfile)
        except IDDAlreadySetError:
            pass

        # The prepended tag on database files used to identify them
        self.database_tag = "DB-"

        # The headings that Simstock expects and the QVariant type of each, and dummy values
        # Format is: "heading-QVariantType-dummyvalue"
        self.headings = ["polygon-None-None",
                         "UID-String-None",
                         "shading-Bool-false",
                         "height-Double-3.0",
                         "wwr-Double-12",
                         "nofloors-Int-1",
                         "wall_const-String-wall_cavity_uninsulated",
                         "roof_const-String-roof_flat_uninsulated",
                         "floor_const-String-ground_floor_solid_uninsulated",
                         "glazing_const-String-glazing_uninsulated",
                         "infiltration_rate-Double-0.7",
                         "ventilation_rate-Double-2.0",
                         "overhang_depth-Double-None"]

        # Load config file
        with open(os.path.join(self.plugin_dir, "config.json"), "r") as read_file:
            self.config = json.load(read_file)
            #TODO: deal with other encodings, specifically utf-8-sig which is used by Windows notepad
            #      or just switch to GUI method



    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = SimstockQGISDialog()
            
            # Check if the buttons were clicked and run function if so
            self.dlg.pbInitialSetup.clicked.connect(self.initial_setup)
            self.dlg.pbRunSim.clicked.connect(self.run_plugin)
            self.dlg.pbOptions.clicked.connect(self.add_fields)
            self.dlg.pbSetcwd.clicked.connect(self.set_cwd)
            self.dlg.label_4.linkActivated.connect(self.open_config)

        # show the dialog
        self.dlg.show()
        
        # Run the dialog event loop
        result = self.dlg.exec_()
        
        # See if OK was pressed
        if result:
            pass #don't do anything if OK was pressed



    def open_config(self):
        """Reveals the config file to the user directly"""
        config_location = os.path.join(self.plugin_dir, "config.json")

        if self.system == "windows":
            subprocess.run(["explorer", "config.json"], cwd=self.plugin_dir)

        if self.system == "darwin": #TODO: needs testing
            subprocess.run(["open", "config.json"], cwd=self.plugin_dir)



    def initial_setup(self):
        # TODO:
        #   - Print out more useful information in the case that failures occured. This will be 
        #      useful if users need to report bugs, and can provide the important info for them.
        #   - Put into functions, and maybe even separate script
        print("Initial setup starting...")
        
        # Set up list to track success of each test
        self.initial_tests = []
        
        # Tracks unimportant issues, unless something fails in which case could be useful to debug
        self.initial_tests_warnings = [] 


        def locate_ep_files():
            """
            Locates all required EnergyPlus files.

            Returns a dictionary where the key is the name of the required file, and the value
            states True or False to indicate whether the file was found or not.
            """
            # List of required EP files according to platform
            if self.system == "windows":
                ep_files = ["Energy+.idd", "energyplus.exe", "energyplusapi.dll", "ReadVarsESO.exe"]
            elif self.system == "darwin":
                ep_files = ["Energy+.idd", "energyplus", "libenergyplusapi.8.9.0.dylib",
                            "libgcc_s.1.dylib", "libgfortran.3.dylib", "libquadmath.0.dylib",
                            "ReadVarsESO"]

            # Initialise dictionary
            d = {}
            for x in ep_files:
                d[x] = True

            # Loop over required files list
            for f in d.keys():
                fp = os.path.join(self.ep_plat_dir, f)
                if os.path.exists(fp):
                    print(f"Located '{f}'")
                else:
                    # Move file if not in expected directory
                    fp = os.path.join(self.ep_plat_dir, "PostProcess", f)
                    if os.path.exists(fp):
                        print(f"Located '{f}'")
                        shutil.move(fp, os.path.join(self.ep_plat_dir, f))
                    else:
                        # Change val to False if the file was not found
                        d[f] = False
            return d


        # This is to select a different EnergyPlus source
        ep_source = "download" # "packaged" or "download" or "user"
        self.ep_plat_dir = os.path.dirname(self.energyplusexe)

        # If not all required EP files were found, source these externally
        if not all(locate_ep_files().values()):

            if ep_source == "packaged":
                # Unzip EnergyPlus according to platform
                EP_zipfile = os.path.join(self.EP_DIR, f"ep8.9_{self.system}.zip")

                print("    Extracting EnergyPlus...")
                with ZipFile(EP_zipfile, "r") as fp:
                    fp.extractall(self.EP_DIR)

                # Delete all EP zipfiles
                [os.remove(f) for f in os.scandir(self.EP_DIR) if f.name[-4:]==".zip"]


            # Download EnergyPlus option
            if ep_source == "download":

                # Delete EP folder (if exists) since not all required files were found
                if os.path.exists(self.ep_plat_dir):
                    shutil.rmtree(self.ep_plat_dir)

                # EP download urls according to platform
                if self.system == "windows":
                    ep_link = "https://github.com/NREL/EnergyPlus/releases/download/v8.9.0/EnergyPlus-8.9.0-40101eaafd-Windows-x86_64.zip"

                elif self.system == "darwin":
                    ep_link = "https://github.com/NREL/EnergyPlus/releases/download/v8.9.0/EnergyPlus-8.9.0-40101eaafd-Darwin-x86_64.tar.gz"

                # Get filename of zipfile from url
                EP_zipfile = os.path.join(self.EP_DIR, ep_link.split("/")[-1])

                # Get user's permission before downloading EnergyPlus
                self.ask_permission()
                if self.permission == "n":
                    self.push_msg("Initial setup failed",
                                  "User permission not granted to download EnergyPlus.",
                                  duration=20)
                    self.initial_tests_warnings.append("User permission not granted to download EnergyPlus.")
                    logging.warning("User permission not granted to download EnergyPlus.")
                    return

                elif self.permission == "y":
                    print("User permission granted to download EnergyPlus.")
                    logging.info("User permission granted to download EnergyPlus.")
                    import requests

                    # Download EnergyPlus if permission given
                    if not os.path.exists(EP_zipfile):
                        r = requests.get(ep_link, stream=True)
                        if r.ok:
                            print("Downloading EnergyPlus...")
                            with open(EP_zipfile, "wb") as f:
                                for chunk in r.iter_content(chunk_size=1024):
                                    f.write(chunk)
                

                if self.system == "windows":

                    # Extract zip archive
                    print("    Extracting EnergyPlus...")
                    with ZipFile(EP_zipfile, "r") as fp:
                        fp.extractall(self.EP_DIR)

                    # Arrange in expected file path structure
                    shutil.move(os.path.join(EP_zipfile[:-4], "EnergyPlus-8-9-0"), self.ep_plat_dir)
                    shutil.rmtree(EP_zipfile[:-4]) #delete empty dir

                if self.system == "darwin":

                    # Extract tar.gz archive
                    #import extracttargz
                    #extracttargz.main()        #this throws an error for some reason
                    print("    Extracting EnergyPlus...")
                    # TODO: feed in name of tar.gz file to script
                    subprocess.run([self.qgis_python_location, os.path.join(self.plugin_dir, "extracttargz.py")])

                    # Arrange in expected file path structure
                    shutil.move(os.path.join(EP_zipfile[:-7], "EnergyPlus-8-9-0"), self.ep_plat_dir)
                    shutil.rmtree(EP_zipfile[:-7]) #delete empty dir
                

                # Check that all required files are present and report status
                clean_up = locate_ep_files()

                # Clean up if all files were located
                if all(clean_up.values()):
                    logging.info("All required EP files found")
                    os.remove(EP_zipfile)
                    to_delete = ["ExampleFiles", "PreProcess", "Documentation", "DataSets", "PostProcess", "WeatherData"]
                    for fdir in to_delete:
                        try:
                            shutil.rmtree(os.path.join(self.ep_plat_dir, fdir))
                        except:
                            pass
                else:
                    not_found = [key for key, value in clean_up.items() if not value]
                    msg = f"Could not locate: {', '.join(not_found)}"
                    self.initial_tests.append(msg)
                    logging.critical(msg)

            if ep_source == "user":
                pass
                #   - Main part is creating user notice to download from link, and provide file path with path selector
                #   - Can use the same code as download, but without download step


        # Psutil excluded for now
        # TODO: include without zip and check for binaries

        # # Unzip psutil as per platform
        # if not os.path.exists(os.path.join(self.scripts_dir, "psutil")):
        #     if self.system == "windows" and platform.machine() == "AMD64":
        #         psutil_zipfile = os.path.join(self.scripts_dir, "psutil_win-64.zip")
        #     elif self.system == "darwin" and platform.machine() == "x86_64":
        #         psutil_zipfile = os.path.join(self.scripts_dir, "psutil_osx-64.zip")
        #     else:
        #         print("Only Windows and macOS x86-64 support psutil. "
        #               f"System: {self.system}-{platform.machine()}.")
        #         psutil_zipfile = None
            
        #     # Only extract if system is supported
        #     if psutil_zipfile is not None:
        #         print("    Extracting psutil...")
        #         with ZipFile(psutil_zipfile, "r") as fp:
        #             fp.extractall(self.scripts_dir)

        #         # Delete all psutil zipfiles
        #         [os.remove(f) for f in os.scandir(self.scripts_dir) if f.name[-4:]==".zip"]
        

        # Module tests
        try:
            print("Pandas version: ", pd.__version__)
        except:
            self.initial_tests.append("Pandas could not be imported. This is likely due to the "
                                      "QGIS version (this problem already exists as an issue on "
                                      "the official QGIS GitHub).\n"
                                      "To fix this, try updating the version of QGIS.")

        try:
            import eppy
            print("Eppy version: ", eppy.__version__)
        except ImportError:
            self.initial_tests.append("Eppy failed to load.")
            
        try:
            import shapely
            print("Shapely version: ", shapely.__version__)
        except ImportError:
            self.initial_tests.append("Shapely failed to load.")
            
        # try:
        #     import psutil
        #     print("Psutil version: ", psutil.__version__)
        # except:
        #     # Do not fail if psutil is not imported, since it is not essential
        #     print("Psutil failed to load - not critical.")
            
        # Test Python script
        test_python = os.path.join(self.plugin_dir, "test_python.py")
        

        # Mac OS specific checks
        if self.system == "darwin":
            # Make E+ application executable
            try:
                chmod_cmd = subprocess.run(["chmod", "+x", self.energyplusexe], check=True)
            except subprocess.CalledProcessError:
                self.initial_tests.append("Chmod command failed on EnergyPlus.")

            # Same for ReadVarsESO
            try:
                chmod_cmd = subprocess.run(["chmod", "+x", self.readvarseso], check=True)
            except subprocess.CalledProcessError:
                self.initial_tests.append("Chmod command failed on ReadVarsESO.")

            # Same for sh script
            mac_verify_ep = os.path.join(self.plugin_dir, "mac_verify_ep.sh")
            try:
                chmod_cmd = subprocess.run(["chmod", "+x", mac_verify_ep], check=True)
            except subprocess.CalledProcessError:
                self.initial_tests.append("Chmod command failed on sh script.")
            
            # Call the sh script to bypass all the security warnings that occur when running E+
            mac_verify_ep_result = subprocess.run(["bash", mac_verify_ep], capture_output=True)
            if mac_verify_ep_result.returncode != 0:
                msg = ("Mac verify EnergyPlus sh script failed, but if ",
                       "EnergyPlus runs correctly then this is not a problem. ",
                       "It is possible that the initial setup was already run before.")
                stderr = mac_verify_ep_result.stderr.decode("utf-8")
                print(msg)
                self.initial_tests_warnings.append(stderr)

            # If Mac uses ARM architecture, check that user has installed Rosetta
            if platform.processor().casefold() == "arm":
                try:
                    if not os.path.exists("/usr/libexec/rosetta"):
                        raise Warning
                    if len(os.listdir("/usr/libexec/rosetta")) == 0:
                        raise Warning
                except Warning:
                    self.initial_tests_warnings.append("This appears to be a Silicon Mac with an ARM processor.\n"
                                                    "Please ensure Rosetta is installed to allow EnergyPlus to run.")
                

        # Run a test to see if E+ works
        shoebox_output = os.path.join(self.plugin_dir, "shoebox-output")
        if os.path.exists(shoebox_output):
            shutil.rmtree(shoebox_output)
        epw_file = os.path.join(self.plugin_dir, "testing.epw")

        # Try running EP
        try:
            run_ep_test = subprocess.run([self.energyplusexe, '-r','-d', shoebox_output, '-w', epw_file, "shoebox.idf"],
                                         cwd=self.plugin_dir)
        except:
            # The above will fail if EP was not found
            pass

        # Check for EP test results
        if not os.path.exists(os.path.join(shoebox_output, "eplusout.err")):
            self.initial_tests.append("EnergyPlus could not run.")
        else:
            print("EnergyPlus test completed successfully")
            logging.info("EnergyPlus test completed successfully")
        

        # Run a test to see if ReadVarsESO works
        try:
            subprocess.run([self.readvarseso], cwd=shoebox_output, check=True)
            print("ReadVarsESO test completed successfully")
            logging.info("ReadVarsESO test completed successfully")
        except:
            # Note: this will fail if EP failed to run - this does not necessarily indicate a 
            # problem with ReadVarsESO
            self.initial_tests.append("ReadVarsESO failed to run.")

        # Delete EP test files
        if os.path.exists(shoebox_output):
            shutil.rmtree(shoebox_output)

        # Test that the QGIS Python works via subprocess
        run_python_test = subprocess.run([self.qgis_python_location, test_python],
                                         capture_output=True,
                                         text=True)
        if run_python_test.stdout != "success\n":
            self.initial_tests.append("Python could not be run.")
        else:
            print("Python test completed successfully")
            logging.info("Python test completed successfully")
        

        # Check if any tests failed and report these if necessary
        if len(self.initial_tests) != 0:
            self.initial_setup_worked = False
            self.push_msg("Initial setup failed",
                          "Some errors have occured - please check the Python console outputs.",
                          qgislevel=Qgis.Critical,
                          printout=False)
            logging.critical(f"Initial setup failed:\n{self.initial_tests}\n{self.initial_tests_warnings}")

            # Print errors to Python console
            print("\nERRORS:")
            [print(error) for error in self.initial_tests]

            # Print warnings to Python console (if any)
            if len(self.initial_tests_warnings) != 0:
                print("\nWARNINGS:")
                [print(warning) for warning in self.initial_tests_warnings]

        else:
            self.initial_setup_worked = True
            self.push_msg("Initial setup complete",
                          "Initial setup completed successfully. Please restart QGIS.",
                          qgislevel=Qgis.Success,
                          duration=20)
            logging.warning(f"Initial setup warnings:\n{self.initial_tests_warnings}")
            logging.info("Initial setup completed successfully")



    def ask_permission(self):
        from .Simstock_QGIS_dialog import PermissionDialog
        self.dlg2 = PermissionDialog()
        self.dlg2.permissionBox.accepted.connect(self.permission_yes)
        self.dlg2.permissionBox.rejected.connect(self.permission_no)
        self.dlg2.exec_()


    def permission_yes(self):
        self.permission = "y"
        #self.dlg2.done(0)
        self.dlg2.close()

    def permission_no(self):
        self.permission = "n"
        self.dlg2.close()



    def add_fields(self):
        """Allows results_mode=False to be passed to add_new_layer()."""

        self.add_new_layer(results_mode=False)



    def push_msg(self,
                 title,
                 text,
                 qgislevel=Qgis.Critical,
                 printout=True,
                 duration=-1):
        """
        Pushes a message to QGIS (and the Python console if printout is True).

        qgislevel options:
            - Qgis.Info
            - Qgis.Warning
            - Qgis.Critical (default)
            - Qgis.Success

        If no duration is specified, message will persist indefinitely.
        """
        # TODO: Use QMessageBox
        # TODO: Include logging here to avoid having to do both manually

        if printout:
            print(title + ": " + text)

        self.iface.messageBar().pushMessage(title,
                                            text, 
                                            level=qgislevel,
                                            duration=duration)



    # def show_messages():
    #     QMessageBox.information(None, "Info", "This is an info message.")
    #     QMessageBox.warning(None, "Warning", "This is a warning.")
    #     QMessageBox.critical(None, "Critical", "This is a critical error!")
    #     reply = QMessageBox.question(None, "Confirm", "Do you want to continue?", 
    #                                 QMessageBox.Yes | QMessageBox.No)
    #     if reply == QMessageBox.Yes:
    #         print("User clicked Yes")
    #     else:
    #         print("User clicked No")



    # def get_user_input():
    #     text, ok = QInputDialog.getText(None, "Enter Email", "Email:", text="user@example.com")
    #     if ok and text:  # If user clicked OK and entered something
    #         print(f"User entered: {text}")
    #         return text
    #     else:
    #         print("User cancelled or entered nothing")
    #         return None  # Handle cases where input is empty or cancelled



    def run_plugin(self):
        """
        This calls all the main functions for the full Simstock plugin process. Overview:
            - Sets up the basic_settings.idf
            - Extracts polygons and input data
            - Performs data checks
            - Saves data to csv
            - Runs Simstock pre-processing and idf geometry scripts
            - Runs EnergyPlus on generated idfs and retrieves simulation results
            - Adds results to a new layer and pushes this back to the QGIS session
        """
        
        # Check if initial setup worked
        # TODO: add a check instead which verifies if everything is in place for Simstock to work
        if self.initial_setup_worked is not None:
            if not self.initial_setup_worked:
                print("Warning: Initial setup previously failed - Simstock may not function correctly.")
        
        # Pandas check in case initial setup was not run
        try:
            _ = pd.DataFrame()
        except:
            self.push_msg("Pandas could not be imported",
                          "This is likely due to the QGIS version (this problem already exists as "
                          "an issue on the official QGIS GitHub).\n"
                          "To fix this, try updating the version of QGIS.")
            return

        # Check if user cwd has been set
        if not self.cwd_set:
            # self.push_msg(title="CWD not set!",
            #               text="Please set the cwd before attempting to run Simstock.",
            #               duration=5)
            QMessageBox.critical(None, "CWD not set!",
                                 "Curent working directory not set! Please set the cwd before "
                                 "attempting to run Simstock.")
            return
        
        # Announce start of process
        self.push_msg("Simstock running",
                      "Simstock is currently running. Please wait...",
                      qgislevel=Qgis.Info,
                      duration=5)
        logging.info("Plugin process started")


        ### BASIC SETTINGS
        # Set up basic settings idf from database materials/constructions
        self.setup_basic_settings()


        ### INPUT DATA
        # Extract polygons and data from attribute table for the selected layer
        dfdict = self.extract_data()
        if dfdict is None:
            return

        # Attribute table input data checks
        dc_message = self.data_checks(dfdict)
        if dc_message is not None:
            self.push_msg("Input data problem", dc_message)
            logging.critical(f"Input data problem: {dc_message}")
            return
        
        # Check that epw file exists
        if not self.check_epw():
            return

        # Extract floor-specific attribute table input data (use columns) if they exist
        dfdict = self.extract_floor_data(dfdict)

        # Strip and lowercase all strings
        dfdict = self.format_strings(dfdict)

        # Save data as csv for Simstock to read
        data = pd.DataFrame(dfdict).rename(columns={"UID":"osgb"})
        data.to_csv(os.path.join(self.plugin_dir, "sa_data.csv"))
        
        
        ### SIMSTOCK
        # Import and run Simstock
        import simstockone as first
        import simstocktwo as second
        first.main()
        self.preprocessed_df = pd.read_csv(os.path.join(self.plugin_dir, "sa_preprocessed.csv"))
        second.main(idf_dir=self.idf_dir)
        

        ### ENERGYPLUS
        # Run E+ simulation, generate .rvi files and run ReadVarsESO
        unique_bis = self.preprocessed_df[self.preprocessed_df["shading"]==False]["bi"].unique()
        self.idf_files = [os.path.join(self.idf_dir, f"{bi}.idf") for bi in unique_bis]
        self.idf_result_dirs = self.run_simulation(multiprocessing=self.dlg.cbMulti.isChecked()) #check if mp checkbox is ticked
        if self.idf_result_dirs is None:
            return


        ### RESULTS
        # Push the results to a new QGIS layer
        success = self.add_new_layer(results_mode=True)

        if success:
            # self.push_msg("Simstock completed",
            #               "Simstock has completed successfully.",
            #               qgislevel=Qgis.Success,
            #               duration=10)
            QMessageBox.information(None, "Simstock completed",
                                    "Simstock has completed successfully.")
            logging.info("Simstock completed successfully\n")



    def extract_data(self):
        """
        Extracts polygons, as well as data from attribute table for the selected layer.

        Raises an error if any of the required fields were not found.
        """
        # Get layer, check exists and format
        self.selectedLayer = self.dlg.mMapLayerComboBox.currentLayer()
        if self.selectedLayer is None:
            self.push_msg("Layer does not exist.", "")
            return
        if not isinstance(self.selectedLayer, QgsVectorLayer):
            self.push_msg("Simstock expects a Vector Layer as input.",
                         f"'{self.selectedLayer.name()}' is not a vector layer.")
            return
        if not self.selectedLayer.isSpatial():
            self.push_msg("Layer has no geometry.",
                         f"'{self.selectedLayer.name()}' has no geometry.")
            return

        # Extract features from layer
        self.features = [feature for feature in self.selectedLayer.getFeatures()]
        
        # Path to qgz file
        path_to_file = QgsProject.instance().absoluteFilePath()
        
        # Extract geometry data from layer as polygons
        polygon = [feature.geometry().asWkt() for feature in self.features]
        
        # Extract all other required Simstock data from layer
        headings = [heading.split("-")[0] for heading in self.headings]
        dfdict = {}
        dfdict[headings[0]] = polygon
        for heading in headings[1:]:
            try:
                dfdict[heading] = [feature[heading] for feature in self.features]

            except KeyError:
                self.push_msg(f"Field '{heading}' not found in the attribute table",
                               "Use 'Add Fields' to add the required Simstock fields to the layer.")
                logging.critical(f"Field '{heading}' not found in the attribute table")
                return
                # TODO: If layers are saved as shapefile, the field names can be shortened due to 
                #       a character limit. Include a warning. Should the field names be shortened?
        
        logging.info(f"Extracted data from layer '{self.selectedLayer.name()}'")
        return dfdict
    


    def extract_floor_data(self, dfdict):
        """
        Extracts floor-specific attributes, i.e. use columns.

        Expects this to be in the format "FLOOR_X: use".
        """
        # TODO: What happens later down the line if use cols for only some of the floors are missing?

        max_floors = max(dfdict["nofloors"])
        for x in range(max_floors):
            heading = f"FLOOR_{x+1}: use"
            try:
                dfdict[heading] = [feature[heading] for feature in self.features]
            except KeyError:
                print("Could not find 'use' column(s). Assuming all zones to be 'Dwell'.\n"
                      "To add the 'use' columns, fill out the 'nofloors' column and then use "
                      "'Add Fields' afterwards.")
        return dfdict



    def data_checks(self, dfdict):
        """
        Verifies that the input values in the attribute table are valid for the operation of Simstock.

        Returns:
            - None if all checks pass.
            - If a check fails, it returns a message string containing info on changes that need to 
              be made - this can be pushed to the user.
        """

        # TODO: This can probably be streamlined and written to auto-update by utilising the self.headings
        #       Maybe change the self.headings into a nested dictionary

        # Checks to do for all attrs:
        #   - Missing values
        #       - For String it is ""
        #       - For Int, Double it is type QVariant - TODO: can the check be more specific?
        #   - Invalid values

        # Check for duplicate UIDs
        if len(dfdict["UID"]) != len(set(dfdict["UID"])):
            return ("Duplicate UIDs detected! Do not edit the UID column.\n"
                    "To regenerate these, delete the entire column and use 'Add Fields' again.")

        # Check values which are required for all polygons
        for y, value in enumerate(dfdict["shading"]):

            # Shading invalid
            if isinstance(value, str) and value.lower() not in ["false", "true"]:
                return ("Values in the 'shading' field should be 'true' or 'false'.\n"
                       f"Received: '{value}' for {dfdict['UID'][y]}.")
            
            # Shading missing
            if isinstance(value, QVariant):
                return ("Values in the 'shading' field should be 'true' or 'false'.\n"
                       f"Check value for {dfdict['UID'][y]}.")
            
            # Height missing
            if isinstance(dfdict["height"][y], QVariant):
                return (f"Check 'height' value for {dfdict['UID'][y]}.")
            
            # Height invalid
            if dfdict["height"][y] == 0:
                return (f"Height value for {dfdict['UID'][y]} is zero.")
            
            # UID missing
            if dfdict["UID"][y] == "":
                return ("UID(s) missing! Do not edit the UID column.\n"
                        "To regenerate these, delete the entire column and use 'Add Fields' again.")
        

        # Check if all polygons are shading
        if len(set(dfdict["shading"])) == 1 and str(list(set(dfdict["shading"]))[0]).lower() == "true":
            return ("Polygons cannot all be shading! Ensure that some are set to 'false'.")


        # Check values which are required for only non-shading polygons
        for y, value in enumerate(dfdict["shading"]):
            if str(value).lower() == "false":

                # WWR missing
                if isinstance(dfdict["wwr"][y], QVariant):
                    return (f"Check 'wwr' value for {dfdict['UID'][y]}")
                
                # wall_const missing
                if dfdict["wall_const"][y] == "":
                    return (f"Check 'wall_const' value for {dfdict['UID'][y]}. "
                            "Each construction element must now be specified separately.")
                # roof_const missing
                if dfdict["roof_const"][y] == "":
                    return (f"Check 'roof_const' value for {dfdict['UID'][y]}. "
                            "Each construction element must now be specified separately.")
                # floor_const missing
                if dfdict["floor_const"][y] == "":
                    return (f"Check 'floor_const' value for {dfdict['UID'][y]}. "
                            "Each construction element must now be specified separately.")
                # glazing_const missing
                if dfdict["glazing_const"][y] == "":
                    return (f"Check 'glazing_const' value for {dfdict['UID'][y]}. "
                            "Each construction element must now be specified separately.")
                
                # Ventilation_rate missing
                if isinstance(dfdict["ventilation_rate"][y], QVariant):
                    return (f"Check 'ventilation_rate' value for {dfdict['UID'][y]}")
                
                # Infiltration_rate missing
                if isinstance(dfdict["infiltration_rate"][y], QVariant):
                    return (f"Check 'infiltration_rate' value for {dfdict['UID'][y]}")
                
                # Nofloors missing
                if isinstance(dfdict["nofloors"][y], QVariant):
                    return (f"Check 'nofloors' value for {dfdict['UID'][y]}")
                
                # Nofloors invalid (zero) value
                if dfdict["nofloors"][y] == 0:
                    return (f"Polygon {dfdict['UID'][y]} has zero value for 'nofloors'.")
        
        # Return None if all checks passed
        return
    


    def format_strings(self, dfdict):
        """
        Applies `lower()` and `strip()` to attributes of string type to make all lowercase and
        remove trailing whitespace.

        Uses `self.headings` to find the core fields which are str type and then also appends the
        fields that start with 'FLOOR_'.
        """

        headings_str = []

        # Loop through self headings
        for h in self.headings:
            heading, QVType, _ = h.split("-")

            # Append the fieldname if it is str type and is not the UID field
            if QVType == "String" and heading != "UID":
                headings_str.append(heading)

        # Also append all fields starting with 'FLOOR_' which should just be the use fields
        use_headings = [key for key in dfdict.keys() if key.startswith("FLOOR_")]
        headings_str.extend(use_headings)

        # Apply .lower() and .strip() to all attributes within identified fields (but skip NULLs)
        for heading in headings_str:
            dfdict[heading] = [x.lower().strip() if isinstance(x, str) else x for x in dfdict[heading]]

        return dfdict



    def check_epw(self):
        """
        Checks if the epw weather file exists in the user's cwd.

        Returns True if so, or False if the file is not found.
        """
        # Set epw path from user cwd and specified filename in config file
        self.epw_file = os.path.join(self.user_cwd, self.config["epw"])

        # Check if the file exists
        if not os.path.exists(self.epw_file):
            self.push_msg("Weather epw file not found",
                          "Check that it exists in the cwd and that is spelled correctly in "
                          "the 'config.json' file.",
                          qgislevel=Qgis.Critical,
                          duration=10)
            return False

        # If the file exists
        else:
            return True



    def run_simulation(self, multiprocessing = True):
        """
        Run E+ simulation, generate .rvi files and run ReadVarsESO
        Outputs: a list of directories containing the results for each idf.
        """
        #qgis.utils.iface.messageBar().pushMessage("Running simulation", "EnergyPlus simulation has started...", level=Qgis.Info, duration=3)

        # List of output directory names
        idf_result_dirs = [i[:-4] for i in self.idf_files]

        # Simulate
        simulationscript = os.path.join(self.plugin_dir, "mptest.py")

        t1 = time.time()
        if not multiprocessing:
            print("Running EnergyPlus simulations on a single core...")
            logging.info("Running EnergyPlus simulations on a single core...")
            subprocess.run([self.qgis_python_location, simulationscript, self.user_cwd, "--singlecore"])
        else:
            print("Running EnergyPlus simulations on multiple cores...")
            logging.info("Running EnergyPlus simulations on multiple cores...")
            subprocess.run([self.qgis_python_location, simulationscript, self.user_cwd])
        
        t = round(time.time()-t1, 2)
        print(f"EnergyPlus simulation completed: took {t}s")
        logging.info(f"EnergyPlus simulation completed: took {t}s")
        
        # For debugging
        #with open(os.path.join(self.plugin_dir, "append1.txt"), "a") as f:
        #    f.write(str(out))# + "\n")
        
        #qgis.utils.iface.messageBar().pushMessage("EnergyPlus finished", "EnergyPlus simulation has completed successfully.", level=Qgis.Success)
        return idf_result_dirs



    ### RESULTS HANDLING
    def add_new_layer(self, results_mode=True):
        """
        This currently has the whole results procedure including:
            - Creating a new layer in memory
            - Retrieving the results of interest by thermal zone
            - Pushing the results back to the new layer
            - Pushing the new layer to the QGIS console
            
        This is also now called by the "Add Fields" button with results_mode=False
        TODO: move result fetching fns elsewhere.
        """

        def getzones(idf):
            """Finds thermal zones in idf and outputs numpy array."""
            all_zones = np.array([zone.Name for zone in idf.idfobjects["ZONE"]])
            return all_zones


        def make_allresults_dict():
            """
            Returns a dict where the key is the name of the thermal zone and the value is a df
            containing all results for that zone.
            """
            all_results = {}
            dfs = []

            # Loop through result directories
            for dirpath in self.idf_result_dirs:

                # Get results csv if exists
                # TODO: allow continuation even if EP fails, and load NULL results for that BI
                results_csv=os.path.join(dirpath, "eplusout.csv")
                if not os.path.exists(results_csv) or os.path.getsize(results_csv)==0:
                    # self.push_msg(f"Results for '{os.path.basename(dirpath)}' not found.",
                    #               f"Check '{os.path.join(dirpath, "eplusout.err")}' "
                    #                "EnergyPlus error report file.")
                    QMessageBox.critical(None, f"Results for '{os.path.basename(dirpath)}' not found.",
                                         f"Results for '{os.path.basename(dirpath)}' not found. "
                                          "Check the relevant EnergyPlus error report file.\n\n"
                                          "This can be found at the following path:\n"
                                         f"'{os.path.join(dirpath, "eplusout.err")}'.")
                    logging.critical(f"Results for '{os.path.basename(dirpath)}' not found.")
                    return
                df = pd.read_csv(results_csv)
                dfs.append(df)
                
                # Load corresponding idf file with same name
                idf = IDF(dirpath + ".idf")

                # Get zone names from within the idf
                zonelist = getzones(idf)

                # Loop through the idf zones and look for the corresponding result columns
                for zone in zonelist:
                    zonename = zone.upper() #E+ outputs zone names in caps in results
                    zonecols = [col for col in df.columns if zonename in col]
                    zone_df = df[zonecols]
                    #zone_df["results_path"] = dirpath #add path to results #inprogress
                    all_results[zone] = zone_df

            return all_results, dfs


        def extract_results(all_results):
            """
            Extracts the results of interest from the individual dfs. Returns 
            a dict where the key is the zone name and the value is the results.

            Needs generalising
            """

            def get_result_val(output_name, df):
                """
                Looks into zone result df for a given output. Returns the whole series of values.
                """
                # Find column(s) containing the specified output name
                value_col = [col for col in df.columns if output_name in col]

                # Raise error if no column is found
                if len(value_col) == 0:
                    logging.critical(f"Cannot find {output_name} value for zone '{zone}' in results.")
                    raise RuntimeError(f"Cannot find {output_name} value for zone '{zone}' in results.")

                # If more than one column is found
                if len(value_col) > 1:
                    print(f"Found two values for {output_name} for zone '{zone}' in results.")
                    logging.warning(f"Found two values for {output_name} for zone '{zone}' in results.")

                # Return the column of interest
                series = df[value_col[0]] #should only be one col
                return series


            # Set up empty dict and get post-processing values
            extracted_results = {}
            #cooling_COP = float(self.config["Cooling COP"])
            #grid_factor = float(self.config["Grid factor - kgCO2/kWh"])
            #elec_cost   = float(self.config["Electricity cost - currency/kWh"])

            # Loop over each zone's results df
            for zone, df in all_results.items():
                # Output results definition
                # Get operative temperature and use thresholds to get hours above/below
                operative_series = get_result_val("Zone Operative Temperature", df)
                below = operative_series[operative_series < self.low_temp_threshold].count()
                above = operative_series[operative_series > self.high_temp_threshold].count()

                # below_1 = operative_series[operative_series < self.low_temp_threshold_1].count()
                # below_2 = operative_series[operative_series < self.low_temp_threshold_2].count()
                # below_3 = operative_series[operative_series < self.low_temp_threshold_3].count()
                # below_4 = operative_series[operative_series < self.low_temp_threshold_4].count()

                # above_1 = operative_series[operative_series > self.high_temp_threshold_1].count()
                # above_2 = operative_series[operative_series > self.high_temp_threshold_2].count()
                # above_3 = operative_series[operative_series > self.high_temp_threshold_3].count()
                # above_4 = operative_series[operative_series > self.high_temp_threshold_4].count()

                # Get minimum and maximum temperatures
                min_temp = round(min(operative_series), 2)
                max_temp = round(max(operative_series), 2)
                
                # Get electricity consumption
                elec = get_result_val("Electricity", df).sum()

                # Get hypothetical heating/cooling loads
                heating_load = get_result_val("Heating", df).sum()
                cooling_load = get_result_val("Cooling", df).sum()
                #cooling_demand = cooling_load / cooling_COP #apply COP factor

                # Convert to kWh
                elec = round(elec / (3.6E6), 2)
                heating_load = round(heating_load / (3.6E6), 2)
                cooling_load = round(cooling_load / (3.6E6), 2)

                # # Combine to get total electricity demand
                # energy = elec + heating_load + cooling_demand
                # energy = round(energy / (3.6E6), 2) #convert to kWh

                # # Apply grid factor to get associated CO2 emissions in kg
                # co2_emissions = round(energy * grid_factor, 2)

                # # Apply cost of electricity to get total cost
                # total_cost = round(energy * elec_cost, 2)

                # Path to results #inprogress
                #r_path = df["results_path"][0]

                # Combine extracted results into list
                lst = [below,
                       above,
                       min_temp,
                       max_temp,
                       elec,
                       heating_load,
                       cooling_load] #TODO: this needs to be same order as attr_types, change to dict?
                lst = [float(x) for x in lst] #change type from np float to float
                extracted_results[zone] = lst

            return extracted_results


        def new_attrs_all_floors(max_floors, attr_types, results_mode):
            """
            Creates a result field for each result type up to the max number of floors.
            
            Needs generalising - specifically using float for all result fields. Can do a similar
            thing as with self.headings.
            """
            new_attrs = []

            # Add attributes before floor-specific ones     #TODO: move this out
            if results_mode:

                # Add the built island ref as a result
                new_attrs.append(QgsField('bi_ref', QVariant.String))

                # Add total fields
                new_attrs.append(QgsField('Total electricity consumption (kWh/yr)', QVariant.Double))
                new_attrs.append(QgsField('Total heating load (kWh/yr)', QVariant.Double))
                new_attrs.append(QgsField('Total cooling load (kWh/yr)', QVariant.Double))

            if max_floors is not None:
                # Must add the same number of fields to each feature
                for i in range(max_floors):

                    # Loop over base result types
                    for attr_type in attr_types:

                        # Prepend floor number to result base name
                        attr_name_floor = f"FLOOR_{i+1}: {attr_type}"

                        if results_mode:
                            # Using "Double" type (float) for all results fields
                            new_attrs.append(QgsField(attr_name_floor, QVariant.Double))
                        else:
                            # Using "String" type for all fields (should only be 'use')
                            new_attrs.append(QgsField(attr_name_floor, QVariant.String))

            # Add attributes after floor-specific ones
            # NOTE: that if not all the floor-specific fields are filled out (e.g. if the polygon
            #       has fewer floors) then anything added here will unintentionally end up in the
            #       floor fields. To avoid this, could add manual NULL values.
            #if results_mode:
                #new_attrs.append(QgsField('Results directory', QVariant.String)) #inprogress

            # Get the names of each newly created attribute
            #attr_names = [attr.name() for attr in new_attrs]
            return new_attrs#, attr_names


        def add_results_to_features(fields, results_mode, extracted_results=None):
            """
            Adds the new attributes to the features and populates their values.
            Needs generalising
            """

            # Loop through each feature (polygon)
            for i in range(len(self.features)):

                # Update the feature to gain the new fields object
                self.features[i].setFields(fields, initAttributes=False)
                
                # Grab the attributes from this feature
                feature_attrs = self.features[i].attributes()
                

                if results_mode:
                    # Get the unique id for this feature
                    osgb = self.features[i].attribute("UID")

                    # Log progress
                    print(f"Retrieving results for '{osgb}'...")
                    #logging.info(f"Retrieving results for '{osgb}'...")

                    # Find the BI ref
                    bi_ref = self.preprocessed_df.loc[self.preprocessed_df["osgb"] == osgb, "bi"].values[0]

                    # Collate the new results
                    result_vals = []

                    # Get all the thermal zones belonging to this feature (multifloors)
                    thermal_zones = [zone for zone in extracted_results.keys() if osgb in zone]

                    # Initialise lists for calculating totals
                    elec_tot, heat_tot, cool_tot = [], [], []

                    # Ignore shading blocks
                    if len(thermal_zones) != 0:

                        # Loop through the thermal zones belonging to the feature
                        for j, zone in enumerate(thermal_zones):

                            # Check the order is correct
                            print(f"    Found results for floor {j+1}: '{zone}'")
                            if zone[-1] != str(j+1):    #TODO: this only works for single digit floors
                                logging.warning(f"Floor results are in the wrong order for zone '{zone}'.")

                            # Collect the results for the thermal zone
                            result_vals.extend(extracted_results[zone])

                            # Append values for calculating totals (needs generalising)
                            elec_tot.append(extracted_results[zone][-3])
                            heat_tot.append(extracted_results[zone][-2])
                            cool_tot.append(extracted_results[zone][-1])

                        # Calculate totals
                        #result_vals.append("r_path_here") #inprogress
                        elec_tot = round(sum(elec_tot), 2)
                        heat_tot = round(sum(heat_tot), 2)
                        cool_tot = round(sum(cool_tot), 2)

                        # Construct the final list of result vals
                        result_vals = [bi_ref, elec_tot, heat_tot, cool_tot] + result_vals
                    
                    # Put the results with the rest of the attributes ready for adding
                    feature_attrs.extend(result_vals)
                

                elif not results_mode:
                    # Check if UID values already exist
                    done = False
                    for feature in feature_attrs:
                        # This checks the values themselves rather than the col name
                        # TODO: This is not rigorous enough as it could incorrectly flag, but UID
                        #       field has already been added by this point. Could append to list...
                        if "UID" in str(feature):
                            done = True

                    # Add the UID values if not present
                    if not done:
                        # Note: This relies on the UID column being the first to be added which is
                        #       always true. The above check also avoids adding these values if they
                        #       already exist. If it is necessary to add other values, can use
                        #       [f.name() for f in self.features[i].fields()] to get fields in order.
                        feature_attrs.append(self.unique_ids[i])

                    # Debugging feature to add dummy values to a newly created layer
                    # Note: this fails if some of the columns already exist, but is only for testing
                    debugging = False
                    if debugging:
                        self.push_msg("Debugging mode activated",
                                      "Filling dummy values for each attribute",
                                      qgislevel=Qgis.Info,
                                      printout=False,
                                      duration=10)

                        # Loop over headings, types, dummy vals
                        for headingtypeval in self.headings:
                            htype, val = headingtypeval.split("-")[1:3]

                            # Excludes polygon, UID as it is pre-generated, and overhang depth as it is not necessary
                            if val != "None":

                                # Ensure correct types
                                if htype == "Double":
                                    val = float(val)
                                if htype == "Int":
                                    val = int(val)

                                # Add dummy values
                                feature_attrs.append(val)

                # Set the feature's attributes
                self.features[i].setAttributes(feature_attrs)


        # Set up Eppy
        from eppy.modeleditor import IDF, IDDAlreadySetError
        if self.system in ['windows', 'linux', 'darwin']:
            iddfile = os.path.join(self.EP_DIR, 'ep8.9_{}/Energy+.idd'.format(self.system))
        try:
            IDF.setiddname(iddfile)
        except IDDAlreadySetError:
            pass

        # Change some of the existing attributes if necessary (probably not)
        #self.features[0].setAttribute(1, "text")

        # Set name for new layer to be created
        if results_mode:
            logging.info("Started results processing")
            if self.HeatCool.lower() == "false":
                new_layer_name = self.selectedLayer.name() + "_Simstock-results_HC-Off"
            elif self.HeatCool.lower() == "true":
                new_layer_name = self.selectedLayer.name() + "_Simstock-results_HC-On"
        else:
            # Grab selected layer (in results mode this would have already been done)
            self.selectedLayer = self.dlg.mMapLayerComboBox.currentLayer()
            new_layer_name = self.selectedLayer.name() + "_1"
        
        # Get CRS from old layer
        crs = self.selectedLayer.crs().authid()

        # Create new layer in memory for the results
        mem_layer = QgsVectorLayer(f"Polygon?crs={crs}", new_layer_name, "memory")
        mem_layer_data = mem_layer.dataProvider()

        # Get attributes and fields from original layer
        layer_attrs = self.selectedLayer.dataProvider().fields().toList() # QgsField type
        layer_fields = self.selectedLayer.fields() # QgsFields type
        new_attrs = []


        if results_mode:
            # Needs generalising
            # Extract all results from the csvs by thermal zone
            all_results, dfs = make_allresults_dict()

            # Return False if error encountered
            if all_results is None:
                return False
            
            # Output full results in cwd for external analysis
            df_merged = reduce(lambda left, right: pd.merge(left, right, on="Date/Time", how="outer"), dfs)
            df_merged.to_csv(os.path.join(self.user_cwd, "Simstock_Results_Full.csv"), index=False)

            # Load config stuff and constants required for post-processing
            self.low_temp_threshold = float(self.config["Low temperature threshold"])
            self.high_temp_threshold = float(self.config["High temperature threshold"])

            # self.low_temp_threshold_1 = float(self.config["Low temperature threshold 1"])
            # self.low_temp_threshold_2 = float(self.config["Low temperature threshold 2"])
            # self.low_temp_threshold_3 = float(self.config["Low temperature threshold 3"])
            # self.low_temp_threshold_4 = float(self.config["Low temperature threshold 4"])

            # self.high_temp_threshold_1 = float(self.config["High temperature threshold 1"])
            # self.high_temp_threshold_2 = float(self.config["High temperature threshold 2"])
            # self.high_temp_threshold_3 = float(self.config["High temperature threshold 3"])
            # self.high_temp_threshold_4 = float(self.config["High temperature threshold 4"])

            #currency = self.config["Currency"]

            # Extract only the results of interest from the dfs
            extracted_results = extract_results(all_results)

            # Output results definition
            # The base names of the results fields to be added (floor number will be appended to these)
            attr_types = [f"Hours/yr below {self.low_temp_threshold}C operative temperature",
                          f"Hours/yr above {self.high_temp_threshold}C operative temperature",
                           "Min temperature (degC)",
                           "Max temperature (degC)",
                           "Electricity consumption (kWh/yr)",
                           "Heating load (kWh/yr)",
                           "Cooling load (kWh/yr)"]
            max_floors = int(self.preprocessed_df['nofloors'].max())


        else:
            attr_types = ["use"]
            self.features = [feature for feature in self.selectedLayer.getFeatures()]

            # Create unique IDs (UIDs) for each feature and ensure they are the same length
            padding = len(str(len(self.features)))
            self.unique_ids = [f"UID{str(i).zfill(padding)}" for i in range(len(self.features))]
            
            # Add fields which are not floor-specific
            for field in self.headings:
                heading, QVtype = field.split("-")[:2]
                if heading != "polygon":
                    exec(f"new_attrs.append(QgsField('{heading}', QVariant.{QVtype}))", globals(), locals())

            try:
                # This will only work the 2nd time when the nofloors field is present
                nofloors = [feature["nofloors"] for feature in self.features]
                max_floors = max(nofloors)

                # If the field exists but the values have not yet been filled out
                # then skip creating the floor-specific fields
                if isinstance(max_floors, QVariant):
                    print("Field 'nofloors' detected but no values inputted.")
                    max_floors = None

            except KeyError:
                # In the first instance, the layer won't have the nofloors field
                # So ignore the floor-specific fields for now
                max_floors = None
        

        # Add new attribute types for the results for all floors
        new_attrs.extend(new_attrs_all_floors(max_floors, attr_types, results_mode))

        # TODO: is this intermediate step necessary?
        for new_attr in new_attrs:
            layer_fields.append(new_attr)
        layer_attrs.extend(new_attrs)
        
        # Add the actual result values and push to features
        if results_mode:
            add_results_to_features(layer_fields, results_mode, extracted_results)
        else:
            add_results_to_features(layer_fields, results_mode)
        
        # Add the attributes into the new layer and push it to QGIS
        mem_layer_data.addAttributes(layer_attrs)
        mem_layer.updateFields()
        mem_layer_data.addFeatures(self.features)
        QgsProject.instance().addMapLayer(mem_layer)

        # Check the capabilities of the layer
        #caps = mem_layer.dataProvider().capabilities()
        #if caps & QgsVectorDataProvider.AddFeatures:
        #    print("can")
        
        # Refresh the map if necessary
        if qgis.utils.iface.mapCanvas().isCachingEnabled():
            self.selectedLayer.triggerRepaint()
        else:
            qgis.utils.iface.mapCanvas().refresh()
        
        # Return True if no error encountered
        return True



    def load_database(self, file_exists):
        def csv_to_gpkg(database_csvs, database_layer_names):
            """
            Converts a provided list of csvs to a single geopackage file that can 
            be loaded and edited. May be better to remove this from the plugin 
            and start from the gpkg point.
            """

            # These are necessary arguments for writing gpkg layers
            context = QgsCoordinateTransformContext()
            o_save_options = QgsVectorFileWriter.SaveVectorOptions()

            for i, file in enumerate(database_csvs):

                # Load the csv as a vector layer
                uri = "file:///" + file.path + "?delimiter={}".format(",")
                vlayer = QgsVectorLayer(uri, database_layer_names[i], "delimitedtext")

                # First layer addition to gpkg must be done differently to the rest
                if i == 0:
                    o_save_options.layerName = database_layer_names[i]
                    try:
                        writer = QgsVectorFileWriter.writeAsVectorFormatV3(vlayer, self.gpkg_path[:-5], context, o_save_options)
                    except AttributeError:
                        print("An internal QGIS function was not found. It is likely that you need to update your version of QGIS.")
                        self.iface.messageBar().pushMessage("Internal QGIS function not found",
                                                "An internal QGIS function was not found. It is likely that you need to update your version of QGIS.",
                                                level=Qgis.Critical)
                        raise Exception("An internal QGIS function was not found. It is likely that you need to update your version of QGIS.")

                # Add the remaining layers
                else: 
                    o_save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer 
                    o_save_options.EditionCapability = QgsVectorFileWriter.CanAddNewLayer
                    o_save_options.layerName = database_layer_names[i]
                    writer = QgsVectorFileWriter.writeAsVectorFormatV3(vlayer, self.gpkg_path[:-5], context, o_save_options)

        def load_all_layers_from_gpkg(gpkg, layer_names):
            """Loads all layers from a gpkg file when given their names as a list."""
            for layer in layer_names:
                qgis.utils.iface.addVectorLayer(gpkg + "|layername=" + layer, layer, 'ogr')

        # Find database csvs which contain the default setup idf objects
        self.database_dir = os.path.join(self.plugin_dir, "Database")
        database_csvs = [file for file in os.scandir(self.database_dir)
                         if file.name[-4:] == ".csv" if file.name[:len(self.database_tag)] == self.database_tag]
        database_layer_names = [file.name[:-4] for file in database_csvs] #TODO: remove and use .name method in place

        # If the database gpkg doesn't exit, create it from the csvs
        if not file_exists:
            csv_to_gpkg(database_csvs, database_layer_names)
        
        # Add the database layers
        load_all_layers_from_gpkg(self.gpkg_path, database_layer_names)
    


    def set_cwd(self):
        """
        Sets the input path as the cwd. Used for outputting idfs and database files.
        The cwd will be checked for an existing database file. This will be loaded
        if it exists and a new one created if not.
        """
        # User specified directory for output
        self.user_cwd = self.dlg.mQgsFileWidget.filePath()

        # Check path provided
        if not os.path.exists(self.user_cwd):
            self.push_msg("Selected cwd does not exist",
                          "The selected cwd does not exist - please create the directory if necessary.",
                          duration=10)
            return
        print("Loading database...")

        # Set abspath after checks
        self.user_cwd = os.path.abspath(self.user_cwd)

        # Set idf path
        self.idf_dir = os.path.join(self.user_cwd, "idf_files")

        # First check for existing database layers and remove them
        layers = QgsProject.instance().mapLayers()
        database_layer_ids = []
        for _, layer in layers.items():
            if layer.name()[:len(self.database_tag)] == self.database_tag: #find database layers
                database_layer_ids.append(layer.id())
        QgsProject.instance().removeMapLayers(database_layer_ids)

        # Either load or create the gpkg file
        self.gpkg_name = "Simstock-Database.gpkg"
        self.gpkg_path = os.path.join(self.user_cwd, self.gpkg_name)
        if os.path.exists(self.gpkg_path):
            print("Found existing database file. Loading into workspace...")
            self.load_database(file_exists=True)
        else:
            print("Database file not found. Creating from defaults...")
            self.load_database(file_exists=False)
        
        self.cwd_set = True
        self.push_msg("CWD set",
                     f"Current working directory (cwd) set to: {self.user_cwd}",
                      qgislevel=Qgis.Info,
                      duration=5)



    def setup_basic_settings(self):
        """
        Adds materials and constructions to the basic settings idf based on 
        what is in the database files. This is run when the plugin simulation 
        button is pressed.
        """

        def create_obj_dicts(df, dfname=None):
            """
            Converts database dataframe to a list of dictionaries, ignoring 
            both null and notes fields.
            
            Each dict within the returned list corresponds to a standalone idf object. 
            The keys represent the field names of the idf object.
            """
            dict_list = []

            # Each row represents a standalone idf object, so loop over each
            for _, row in df.iterrows():
                dictionary = {}

                # Loop over elements within the row (i.e. fields of the idf object)
                for i, content in enumerate(row):
                    # Get the row header (i.e. field name)
                    label = row.index[i]

                    # Only add the field if it has content and is not notes
                    # TODO: If a required field has been left blank, this will exclude it
                    #       Either errors will occur later, or Eppy will fill a default value which is unseen by the user
                    if not content == qgis_null and not content == "" and not label == 'Notes': #using qgis nulltype instead of pd here

                        # Next check avoids QGIS bug where it appends "_1" to numbered fields
                        # when importing csv (e.g. "Field_1" becomes "Field_1_1")
                        if dfname is not None and "schedule" in dfname.lower() and label[:5] == "Field":
                            label = label[:-2]

                        # Add to dict    
                        dictionary[label] = content
                
                # Append individual dict corresponding to the idf object
                dict_list.append(dictionary)
            return dict_list

        def get_required_materials(const):
            """
            Looks in constructions and extracts the names of all required materials 
            (i.e. the materials which are used in any of the constructions).
            """
            materials_list = []
            for item in const:
                materials = list(item.values())[1:] #ignore construction names
                materials_list = [y for x in [materials_list, materials] for y in x]

            dict_list=[]
            for b in set(materials_list): #get unique
                d = {}
                d['Name'] = b 
                dict_list.append(d)
            return dict_list

        def add_dict_objs_to_idf(obj_dict, class_name):
            """Adds objects to the idf."""
            for obj in obj_dict:
                idf.newidfobject(class_name,**obj)

        def add_materials(key, material_df, used_materials):
            """Checks against required materials list, and adds those required to the idf."""
            materials = create_obj_dicts(material_df)
            material_type = key.split("-")[-1].replace("_", ":") #change names to match energyplus fields
            
            # Add the material properties to the specific instance of the material
            new_list=[]    
            for mat in materials:
                for item in used_materials:
                    if item['Name']==mat['MatName']: #check if required
                        new_item=dict(item,**mat)
                        new_list.append(new_item) #add if so
                        
            for el in new_list:
                del(el['MatName'])#remove the temporary matname field
                idf.newidfobject(material_type,**el) #expand each dictionary as a new material of the relevant type
            
        def attributes_to_dfs(layers):
            """Converts layer's attribute table into dataframe and appends to a dictionary"""
            dict = {}
            for layer in layers:
                cols = [field.name() for field in layer.fields()]
                datagen = ([f[col] for col in cols] for f in layer.getFeatures())
                df = pd.DataFrame.from_records(data=datagen, columns=cols)
                df.drop(columns=['fid'], inplace=True)
                dict[layer.name()] = df
            return dict
        
        def bool_quick_fix(dfs):
            """To delete"""
            # TODO: work out a permanent fix for this
            # One option is by using the csvt method that is in use for the schedules
            try:
                dfs["DB-Fabric-WINDOWMATERIAL_GLAZING"]["Solar_Diffusing"] = "No"
            except KeyError:
                pass
            try:
                dfs["DB-Loads-PEOPLE"]["Enable_ASHRAE_55_Comfort_Warnings"] = "No"
            except KeyError:
                pass


        # Set up Eppy
        from eppy.modeleditor import IDF, IDDAlreadySetError
        if self.system in ['windows', 'linux', 'darwin']:
            iddfile = os.path.join(self.EP_DIR, 'ep8.9_{}/Energy+.idd'.format(self.system))
        try:
            IDF.setiddname(iddfile)
        except IDDAlreadySetError:
            pass

        # Initialise base idf which will be added to and become the basic_settings.idf for Simstock
        idf = IDF(os.path.join(self.plugin_dir, 'base.idf'))
        
        # Find database layers in current project
        layers = QgsProject.instance().mapLayers()
        database_layers = []
        for _, layer in layers.items():
            if layer.name()[:len(self.database_tag)] == self.database_tag:
                database_layers.append(layer)

        # Convert database attribute tables to dataframes
        dfs = attributes_to_dfs(database_layers)
        # TODO: check for blank, missing, incorrect fields

        # This is a temporary quick fix to avoid certain fields being incorrectly
        # identified as bool type meaning that "No" is changed to "0"
        bool_quick_fix(dfs)

        # Add non-material objects to idf
        for key,df in dfs.items():
            if not "MATERIAL" in key and not "HeatingCooling" in key:
                df = dfs[key]
                class_name = key.split("-")[-1].replace("_", ":") #change names to match energyplus fields
                obj_dict = create_obj_dicts(df, key)
                add_dict_objs_to_idf(obj_dict, class_name)

                # Get materials used in constructions
                if "CONSTRUCTION" in key:
                    used_materials = get_required_materials(obj_dict)

        # Add materials to idf
        for key, df in dfs.items():
            if "MATERIAL" in key:
                add_materials(key, df, used_materials)

        # Check whether heating and cooling setpoints are to be included
        self.HeatCool = str(dfs["DB-HeatingCooling-OnOff"].iloc[0,0]).strip()
        if not isinstance(self.HeatCool, str):
            print("type ", type(self.HeatCool), self.HeatCool)
            raise NotImplementedError(f"self.HeatCool is {type(self.HeatCool)} type")

        # Choose heating & cooling setpoint schedules according to check
        if self.HeatCool.lower() == "false":
            print("Heating and cooling are not activated.")
            thermostats = idf.idfobjects["ThermostatSetpoint:DualSetpoint"]
            for thermostat in thermostats:
                # Swap the names
                thermostat.Heating_Setpoint_Temperature_Schedule_Name = "Dwell_Heat_Off"
                thermostat.Cooling_Setpoint_Temperature_Schedule_Name = "Dwell_Cool_Off"

        elif self.HeatCool.lower() == "true":
            # Schedules already have the correct names in this case
            print("Heating and cooling are activated.")

        # Save idf
        idf.saveas(os.path.join(self.plugin_dir, 'basic_settings.idf'))
        
"""
# For creating the csvt files:
lst = ['"String"']*103
s = ",".join(lst)
with open("test.csv", 'w') as f:
    f.write(s)
"""