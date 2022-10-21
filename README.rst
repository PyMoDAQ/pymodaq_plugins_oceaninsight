pymodaq_plugins_oceaninsight (Ocean Insight (Optics) Spectrometers)
###################################################################

.. image:: https://img.shields.io/pypi/v/pymodaq_plugins_oceaninsight.svg
   :target: https://pypi.org/project/pymodaq_plugins_oceaninsight/
   :alt: Latest Version

.. image:: https://readthedocs.org/projects/pymodaq/badge/?version=latest
   :target: https://pymodaq.readthedocs.io/en/stable/?badge=latest
   :alt: Documentation Status

.. image:: https://github.com/PyMoDAQ/pymodaq_plugins_oceaninsight/workflows/Upload%20Python%20Package/badge.svg
    :target: https://github.com/PyMoDAQ/pymodaq_plugins_oceaninsight

PyMoDAQ plugin for OceanInsight (OceanOptics) spectrometers


Authors
=======

* Sebastien J. Weber
* Nicolas Tappy

Instruments
===========
Below is the list of instruments included in this plugin.
Url: https://www.oceaninsight.com/products/spectrometers/

Viewer1D
++++++++

* **Omnidriver**: Control of Spectrometer using the Omnidriver library (should be installed)
* **Seabreeze** : If the Omnidriver library is not available, a plugin implementation based on seabreeze is provided: https://python-seabreeze.readthedocs.io/en/latest/index.html
