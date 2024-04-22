# q-delta-lake
QGIS plugin for loading data from delta shares.

Note: A lot of the setup and code comes from https://gitlab.com/Oslandia/qgis/qduckdb.
Thanks, Oslandia!

See the README.txt in the plugin directory for more information.

For installing the embedded external packages, use:

`python -m pip install --no-deps -U -r requirements/embedded.txt -t delta_lake/embedded_external_libs`

Please use the QGIS installed Python version to execute this, so for example:

`/Applications/QGIS.app/Contents/MacOS/bin/python -m pip install --no-deps -U -r requirements/embedded.txt -t delta_lake/embedded_external_libs`
