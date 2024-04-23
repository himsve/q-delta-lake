## Plugin for connecting to delta shares such as made available by Databricks.

To connect to Delta Shares, you'll need a secure connection profile file. This file acts like a digital key and will be provided by your system administrators.

Treat this file with the same care as your password. It grants access to all data shared through Delta Shares.

## Usage:
- Please start connecting to delta shares by opening menu Database->Delta Lake->Delta Share
- Specify the location of your connection profile in the file browser field
- Select the table from which you want to use data (the selection box will be prefilled with the tables you have access to through your credential file)
- Specify the EPSG id which has been used to define the geometries
- All text fields can be amended if needed, the selection boxes are just helper functions

## Important:
- Spaces are not supported in the connection profile path due to a bug in the delta sharing packages
- Databricks or rather Delta Tables do not know about geometry datatypes
- Please specify your geometries as WKT in one of the database table columns
- Mark the column with the geometry data contents with the phrase '<geometry>' in the column comment (alter table <catalog>.<schema>.<table> alter column <geometry_column> comment '...<geometry>...';)

## Requirements
- Make sure you have these Python packages installed in the QGIS Python environment:
  1. delta-sharing==1.0.3
  2. shapely==2.0.3
  3. pandas==2.2.1
- See requirements.txt, you can do `pip install -r requirements` to install these packages

## Troubleshooting installation

If you use a bundled Python interpreter as on macOS, please make sure you use the **QGIS installed version of
the python interpreter**.

I also noticed that the upgrade of 'shapely' may not always work as expected.

When in doubt, follow these manual steps, starting from a fresh install of QGIS, macOS as base system:
1. install QGIS package
2. /Applications/QGIS.app/Contents/MacOS/bin/pip3 uninstall shapely
3. /Applications/QGIS.app/Contents/MacOS/bin/pip3 install shapely==2.0.3
4. /Applications/QGIS.app/Contents/MacOS/bin/pip3 install delta-sharing==1.0.3
5. install this plugin from the QGIS plugin repository

