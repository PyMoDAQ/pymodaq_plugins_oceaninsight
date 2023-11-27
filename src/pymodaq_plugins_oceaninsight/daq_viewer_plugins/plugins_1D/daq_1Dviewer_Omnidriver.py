from qtpy import QtWidgets
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
import numpy as np
from collections import OrderedDict
from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo
from pymodaq.utils.data import DataFromPlugins, Axis, DataToExport
import sys
import clr
from easydict import EasyDict as edict


class DAQ_1DViewer_Omnidriver(DAQ_Viewer_base):
    """PyMoDAQ plugin controlling spectrometers from OceanOptics and using their OmniDriver wrapper ('NETOmniDriver-NET40')
    The wrapper is interfaced using the clr package and then importing Omnidriver as a standart python package
    https://oceanoptics.com/api/omnidriver/index.html?overview-summary.html

    The plugin enables the discovery of any connected usb spectrometers and can control them in parallel. It extracts the
    calibrated wavelength and will export datas that will be plotted with respect to this wavelengths vector.

    Used methods from the wrapper:
    ------------------------------
     setIntegrationTime
     getIntegrationTime

    See Also
    --------
    utility_classes.DAQ_Viewer_base
    """
    omnidriver_path = 'C:\\Program Files\\Ocean Optics\\OmniDriver\\OOI_HOME'
    try:
        sys.path.append(omnidriver_path)
        clr.AddReference("NETOmniDriver-NET40")
        import OmniDriver as omnidriver

    except:
        omnidriver = None

    params = comon_parameters + [
        {'title': 'Omnidriver path:', 'name': 'omnidriver_path', 'type': 'browsepath', 'value': omnidriver_path},
        {'title': 'N spectrometers:', 'name': 'Nspectrometers', 'type': 'int', 'value': 0, 'default': 0, 'min': 0},
        {'title': 'Spectrometers:', 'name': 'spectrometers', 'type': 'group', 'children': []},
    ]

    hardware_averaging = True

    def ini_attributes(self):

        self.controller: self.omnidriver.NETWrapper = None
        self.spectro_names = []  # contains the spectro name as returned from the wrapper
        self.spectro_id = []  # contains the spectro id as set by the ini_detector method and equal to the Parameter name

    def commit_settings(self, param):
        """

        """
        if param.name() == 'exposure_time':
            ind_spectro = self.spectro_id.index(param.parent().name())
            self.controller.setIntegrationTime(ind_spectro, param.value() * 1000)

            param.setValue(self.controller.getIntegrationTime(ind_spectro) / 1000)


        elif param.name() == 'omnidriver_path':
            try:
                sys.path.append(param.value())
                clr.AddReference("NETOmniDriver-NET40")
                import OmniDriver
                self.omnidriver = OmniDriver
            except:
                pass

    def ini_detector(self, controller=None):
        """
            Initialisation procedure of the detector updating the status dictionnary.

            See Also
            --------
            set_Mock_data, daq_utils.ThreadCommand
        """
        if self.settings['controller_status'] == "Slave":
            if controller is None:
                raise Exception('no controller has been defined externally while this axe is a slave one')
            else:
                self.controller = controller
        else:  # Master stage

            self.controller = self.omnidriver.NETWrapper()

            N = self.controller.openAllSpectrometers()
            self.settings.child('Nspectrometers').setValue(N)
            self.spectro_names = []
            self.spectro_id = []
            data_init = DataToExport('Spectro')
            for ind_spectro in range(N):
                name = self.controller.getName(ind_spectro)
                self.spectro_names.append(name)
                self.spectro_id.append('spectro{:d}'.format(ind_spectro))

                exp_max = self.controller.getMaximumIntegrationTime(ind_spectro)
                exp_min = self.controller.getMinimumIntegrationTime(ind_spectro)
                exp = self.controller.getIntegrationTime(ind_spectro) / 1000
                wavelengths = self.get_xaxis(ind_spectro)
                data_init.append(DataFromPlugins(name=name, data=[np.zeros_like(wavelengths)], dim='Data1D',
                                                 axes=[Axis(data=wavelengths, label='Wavelength', units='nm')]
                                                 ))
                for ind in range(2):  # this is to take into account that adding it once doen't work
                    # (see pyqtgraph Parameter...)
                    try:
                        self.settings.child('spectrometers').addChild(
                            {'title': name, 'name': 'spectro{:d}'.format(ind_spectro), 'type': 'group', 'children': [
                                {'title': 'grab spectrum:', 'name': 'grab', 'type': 'bool', 'value': True},
                                {'title': 'Exposure time (ms):', 'name': 'exposure_time', 'type': 'int',
                                 'value': int(exp), 'min': int(exp_min / 1000), 'max': int(exp_max / 1000)},
                            ]
                             })
                    except:
                        pass

                QtWidgets.QApplication.processEvents()
                # init viewers
            if N == 0:
                raise Exception('No detected hardware')
            self.dte_signal_temp.emit(data_init)

        initialized = True
        info = ''
        return info, initialized


    def get_xaxis(self, ind_spectro):
        wavelengths_chelou = self.controller.getWavelengths(ind_spectro)
        wavelengths = np.array([wavelengths_chelou[ind] for ind in range(len(wavelengths_chelou))])

        return wavelengths

    def close(self):
        """
        """
        if self.controller is not None:
            self.controller.closeAllSpectrometers()

    def grab_data(self, Naverage=1, **kwargs):
        """

        """
        try:
            dte = DataToExport('Spectro')
            for ind_spectro in range(len(self.spectro_names)):
                if self.settings.child('spectrometers', 'spectro{:d}'.format(ind_spectro), 'grab').value():
                    self.controller.setScansToAverage(ind_spectro, Naverage)
                    data_chelou = self.controller.getSpectrum(ind_spectro)
                    data_array = np.array([data_chelou[ind] for ind in range(len(data_chelou))])
                    dte.append(DataFromPlugins(name=self.spectro_names[ind_spectro], data=[data_array], dim='Data1D'))
                    QtWidgets.QApplication.processEvents()

            self.dte_signal.emit(dte)

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [getLineInfo() + str(e), "log"]))

    def stop(self):
        """

        """
        for ind_spec, name in enumerate(self.spectro_names):
            self.controller.stopAveraging(ind_spec)


if __name__ == '__main__':
    main(__file__)