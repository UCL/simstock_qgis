# Simstock QGIS Plugin Documentation

## Installation, setup and testing
### Supported QGIS versions
The plugin has been tested on a range of QGIS versions, on both Windows and Mac operating systems. The supported versions of QGIS are any LTR (long-term release) between QGIS LTR 3.10 and the latest QGIS LTR 3.22.

The non-LTR versions are likely to work too, however sometimes the Python versions and associated packages in these versions differ from the LTR versions.

###  Installation
  
1. Also search for `Plugin Reloader' and tick the box when it shows up.
    
2. After ticking the boxes, you will need to restart QGIS.
    
3. If the Simstock QGIS plugin has successfully been installed, you should be able to see it listed under the `Plugins' list as well as a new icon on the toolbar.
    
4. The plugin will now need to be tested - see the next section for information.


### Initial setup
Before running anything, make sure that the QGIS Python Console is open as there will be outputs here that will be useful to read. It should open automatically when the plugin is launched, but if not, you can do this by clicking **Plugins $\rightarrow$ Python Console** in the top bar of QGIS.

When the plugin is launched, you will see an **Initial Setup** button. This will run checks to verify that all the dependencies are working as expected.

Click the **Initial Setup** button and watch the Python console for any errors. If any of the steps fail, they should be reported here. If all checks passed, a green success message should show up in the QGIS console. The plugin should now be fully functioning - though you may need to restart QGIS for a final time.


## Using the plugin
### Important notes
There are some important things to note when using the plugin:
* **Python Console**: When using the plugin, always have the Python console open. This will output information about what the plugin is doing. It should open by default when the plugin is launched, but if not, you can do this by clicking Plugins $\rightarrow$ Python Console in the top bar of QGIS.
* **Python Errors**: If an error occurs, a yellow notification appears in QGIS. The Python error can be viewed by clicking 'Stack Trace'. This should give information about what is causing the error.
* **Plugin Reloader**: Make sure the Plugin Reloader is installed (see Section~\ref{section:installation}). If the Simstock plugin stops functioning correctly, reload it using the plugin reloader.


# TODO:
* Add remaining documentation sections
* Update documentation to latest plugin version
* Replace any LATEX syntax
* Insert images