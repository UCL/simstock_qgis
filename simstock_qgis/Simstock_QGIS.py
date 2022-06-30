# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SimstockQGIS
                                 A QGIS plugin
 Feeds QGIS data into Simstock
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2022-05-17
        git sha              : $Format:%H$
        copyright            : (C) 2022 by UCL
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
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QVariant
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from qgis.core import QgsProject, QgsVectorDataProvider, QgsVectorLayer, QgsField, QgsFields #to get layers

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .Simstock_QGIS_dialog import SimstockQGISDialog
import os.path

#my imports
import venv
import subprocess
import pandas as pd
import platform
import sys
import multiprocessing as mp
import qgis.utils
from qgis.core import Qgis
import time

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
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        
        # Update path to access Simstock scripts
        sys.path.insert(0, self.plugin_dir)
        
        # Update path to packaged eppy
        eppy_dir = os.path.join(self.plugin_dir, "eppy-scripts")
        sys.path.append(eppy_dir)
        
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
        
        #initial setup checker
        self.initial_setup_worked = None
        self.simulation_started = None
        
        # Startup E+ stuff
        self.EP_DIR = os.path.join(self.plugin_dir, "EnergyPlus")
        idf_dir = os.path.join(self.plugin_dir, "idf_files")
        self.epw_file = os.path.join(self.plugin_dir, "GBR_ENG_London.Wea.Ctr-St.James.Park.037700_TMYx.2007-2021.epw")
        files = os.scandir(os.path.abspath(idf_dir))
        self.idf_files = [file.path for file in files if file.name[-4:] == ".idf"]

        # Find the computer's operating system and find energyplus version
        self.system = platform.system().lower()
        if self.system in ['windows', 'linux', 'darwin']:
            self.energyplusexe = os.path.join(self.EP_DIR, 'ep8.9_{}/energyplus'.format(self.system))
        
        # Locate QGIS Python, differs by OS
        qgis_python_dir = sys.exec_prefix
        if self.system == "windows":
            self.qgis_python_location = qgis_python_dir + r"\python"
        if self.system == "darwin":
            self.qgis_python_location = qgis_python_dir + "/bin/python3"
        
    
    def initial_setup(self):
        print("Initial setup button pressed")
        
        # Set up list to track success of each test
        self.initial_tests = []
        
        # Module tests
        print("Pandas version: ", pd.__version__)
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
            
        # Find QGIS Python location to override default Python in path        
        test_python = os.path.join(self.plugin_dir, "test_python.py")
        
        if self.system == "darwin":
            # Make E+ application executable
            try:
                chmod_cmd = subprocess.run("chmod +x '%s'" % self.energyplusexe, shell=True, check=True)
            except subprocess.CalledProcessError:
                self.initial_tests.append("Chmod command failed.")
            
            # Run a test to see if E+ works. It is likely the user will need to permit the program in system prefs
            shoebox_idf = os.path.join(self.plugin_dir, "shoebox.idf")
            shoebox_output = os.path.join(self.plugin_dir, "shoebox-output")
            run_ep_test = subprocess.run([self.energyplusexe, '-r','-d', shoebox_output, '-w', self.epw_file, shoebox_idf])
            if not os.path.exists(os.path.join(shoebox_output, "eplusout.err")):
                self.initial_tests.append("EnergyPlus could not run.")
            
            # Test that the QGIS Python works via subprocess
            run_python_test = subprocess.run([self.qgis_python_location, test_python], capture_output=True, text=True)
            if run_python_test.stdout != "success\n":
                self.initial_tests.append("Python could not be run.")
            
        if self.system == "windows":
            # Test that the QGIS Python works via subprocess
            run_python_test = subprocess.run([self.qgis_python_location, test_python], capture_output=True, text=True)
            if run_python_test.stdout != "success\n":
                self.initial_tests.append("Python could not be run.")
        
        if len(self.initial_tests) != 0:
            qgis.utils.iface.messageBar().pushMessage("Initial setup failed", "Some errors have occured - please check the Python console outputs.", level=Qgis.Critical, duration=5)
            self.initial_setup_worked = False
            for error in self.initial_tests:
                print("\n" + error + "\n")
        else:
            self.initial_setup_worked = True
            qgis.utils.iface.messageBar().pushMessage("Initial setup complete", "Initial setup completed successfully. Please restart QGIS.", level=Qgis.Success, duration=5)
            print("Initial setup completed successfully. Please restart QGIS.")

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
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/Simstock_QGIS/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Simstock'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Simstock QGIS'),
                action)
            self.iface.removeToolBarIcon(action)


    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = SimstockQGISDialog()

        # show the dialog
        self.dlg.show()
        
        # Check if the initial setup button was clicked and run function if so
        self.dlg.pbInitialSetup.clicked.connect(self.initial_setup)

        # Check if the run simulation button was clicked and run function if so
        self.dlg.pbRunSim.clicked.connect(self.run_simulations)
        
        # Run the dialog event loop
        result = self.dlg.exec_()
        
        # See if OK was pressed
        if result:
            pass
            
    def run_ep(self, idf_file):
        output_dir = idf_file[:-4]
        subprocess.run([self.energyplusexe, '-r','-d', output_dir, '-w', self.epw_file, idf_file])

    def run_simulations(self):
        # Button signal is sent twice; this attempts to prevent function launching twice in quick succession
        time_now = time.perf_counter()
        
        if self.simulation_started is not None and time_now - self.simulation_started < 5:
            print("Button signal sent twice in quick succession - ignoring.")
            
        else:
            qgis.utils.iface.messageBar().pushMessage("Simstock running...", "Simstock is currently running. Please wait...", level=Qgis.Info)
            self.simulation_started = time.perf_counter()
            
            # Check if initial setup worked
            if self.initial_setup_worked is not None:
                if not self.initial_setup_worked:
                    raise RuntimeError("Initial setup failed! Cannot run Simstock.")
            
            # Try setting up venv
            #venv.create(os.path.join(self.plugin_dir, "virtenv"))#, system_site_packages=True)#, with_pip=True)
            #subprocess.run("python -m venv --copies %s" % venvdir, capture_output=True)
            
            # Check packages
            #subprocess.run(r"python -m pip uninstall eppy > C:\Users\biscu\Documents\phd\Internship\qgisloggy.txt", capture_output=True, shell=True, check=True)
            #subprocess.run(r"python -m pip list >> C:\Users\biscu\Documents\phd\Internship\piplistnew.txt", shell=True)
            #subprocess.run(r"python -m pip show pandas >> C:\Users\biscu\Documents\phd\Internship\pandas-upgraded.txt", shell=True)
            
            
            
            ### EXTRACT DATA
            # Get layer, check exists and extract features
            self.selectedLayer = self.dlg.mMapLayerComboBox.currentLayer()
            if self.selectedLayer is None:
                raise RuntimeError("Layer does not exist.")
            if not isinstance(self.selectedLayer, QgsVectorLayer):
                raise TypeError("Simstock expects a Vector Layer as input.")
            self.features = [feature for feature in self.selectedLayer.getFeatures()]
            
            # Path to qgz file
            path_to_file = QgsProject.instance().absoluteFilePath()
            
            # User specified directory for output
            dirpath = self.dlg.mQgsFileWidget.filePath()
            
            # Extract geometry data from layer as polygons
            polygon = [feature.geometry().asWkt() for feature in self.features]
            
            # Extract all other required Simstock data from layer
            headings = ["polygon", "osgb", "shading", "height", "wwr", "nofloors", "construction"]
            dfdict = {}
            dfdict[headings[0]] = polygon
            for heading in headings[1:]:
                try:
                    dfdict[heading] = [feature[heading] for feature in self.features]
                except KeyError:
                    raise Exception("Attribute '%s' was not found in the attribute table. Check that it is present and spelled correctly and try again." % heading)
            data = pd.DataFrame(dfdict)
            
            # Save data as csv for Simstock to read
            data.to_csv(os.path.join(self.plugin_dir, "sa_data.csv"))
            
            
            
            ### SIMSTOCK
            # Import and run Simstock
            import simstockone as first
            import simstocktwo as second
            first.main()
            second.main()
            
            
            
            ### SIMULATION
            qgis.utils.iface.messageBar().pushMessage("Running simulation", "EnergyPlus simulation has started...", level=Qgis.Info, duration=3)
            time.sleep(5) #sleep so that messages can be pushed to QGIS before it freezes during sim
            # Single core
            #for i, idf_file in enumerate(self.idf_files):
            #    print(f"Starting simulation {i+1} of {len(self.idf_files)}")
            #    self.run_ep(idf_file)
            
            # Parallel processing
            multiprocessingscript = os.path.join(self.plugin_dir, "mptest.py")
            out = subprocess.run([self.qgis_python_location, multiprocessingscript], capture_output=True, text=True)
            #with open(os.path.join(self.plugin_dir, "append1.txt"), "a") as f:
            #    f.write(str(out) + "\n")
            qgis.utils.iface.messageBar().pushMessage("EnergyPlus finished", "EnergyPlus simulation has completed successfully.", level=Qgis.Success)
            
            
            
            ### RESULTS HANDLING
            # Change some of the features if necessary (probably not)
            #self.features[0].setAttribute(1, "text")
            
            # Create new layer in memory for the results
            mem_layer = QgsVectorLayer("Polygon?crs=epsg:4326", "results_layer", "memory")
            mem_layer_data = mem_layer.dataProvider()
            attr = self.selectedLayer.dataProvider().fields().toList() # QgsField type
            fields = self.selectedLayer.fields() # QgsFields type
            
            # Add new attributes for the results
            new_attrs = [QgsField('bi_ref', QVariant.String), QgsField('results', QVariant.Double)]
            for new_attr in new_attrs:
                fields.append(new_attr)
            attr.extend(new_attrs)
            
            # Set the attribute values themselves
            for i in range(len(self.features)):
                #update the feature to gain the new fields object
                self.features[i].setFields(fields, initAttributes=False)
                #grab the attributes from this feature
                attrs = self.features[i].attributes()
                #append the new values
                attrs.append("bi_ref_here")
                attrs.append(2.5235245)
                self.features[i].setAttributes(attrs)
            
            # Add the attributes into the new layer and push it to QGIS
            mem_layer_data.addAttributes(attr)
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
            
            qgis.utils.iface.messageBar().pushMessage("Simstock completed", "Simstock has completed successfully.", level=Qgis.Success)
                