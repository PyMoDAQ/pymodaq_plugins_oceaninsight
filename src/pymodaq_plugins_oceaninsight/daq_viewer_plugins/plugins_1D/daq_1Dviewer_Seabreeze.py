import numpy as np
from easydict import EasyDict as edict
from pymodaq.daq_utils.daq_utils import ThreadCommand, getLineInfo, DataFromPlugins, Axis
from pymodaq.daq_viewer.utility_classes import DAQ_Viewer_base, comon_parameters, main
from timeit import timeit

# explicitly request cseabreeze
import seabreeze
seabreeze.use('cseabreeze')
from seabreeze.spectrometers import Spectrometer, list_devices


class DAQ_1DViewer_Seabreeze(DAQ_Viewer_base):
    """
    """
    # Upon initialisation
    devices = list_devices()

    #Supports pseudo hardware-averaging
    hardware_averaging = True

    params = comon_parameters + [
        {'title': 'Device:', 'name': 'device', 'type': 'list', 'limits': devices},
        {'title': 'Integration (ms):', 'name': 'integration', 'type': 'float', 'value': 1.0},
        {'title': 'Advanced:', 'name': 'advanced', 'type': 'group', 'children': [
            {'title': 'Serial Number:', 'name': 'serial_number', 'type': 'str', 'value': "", 'readonly': True},
            {'title': 'Non Linearity correction:', 'name': 'correct_non_linearity', 'type': 'bool', 'value': False},
            {'title': 'Max Intensity', 'name': 'max_intensity', 'type': "float", 'value': 65535, 'readonly': True},
            {'title': 'Pixels:', 'name': 'pixels', 'type': 'int', 'value': 2048, 'readonly': True},
            {'title': 'Dark Channels:', 'name': 'dark_channels', 'type': 'int', 'value': 10, 'readonly': True},
            {'title': 'Readout Time (ms)', 'name': 'readout_time', 'type': 'float', 'value': 666, 'readonly': True},
        ]}
    ]

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)
        self.x_axis = None

    def commit_settings(self, param):
        """
        """
        if param.name() == "integration":
            self.controller.integration_time_micros(param.value() * 1000)
            # There is no way to get feedback from the spectrometer on the currently set integration time
        # elif ...
        ##

    def ini_detector(self, controller=None):
        """Detector communication initialization

        Parameters
        ----------
        controller: (object) custom object of a PyMoDAQ plugin (Slave case). None if only one detector by controller (Master case)

        Returns
        -------
        self.status (edict): with initialization status: three fields:
            * info (str)
            * controller (object) initialized controller
            *initialized: (bool): False if initialization failed otherwise True
        """

        try:
            self.status.update(edict(initialized=False, info="", x_axis=None, y_axis=None, controller=None))
            if self.settings.child('controller_status').value() == "Slave":
                if controller is None:
                    raise Exception('no controller has been defined externally while this detector is a slave one')
                else:
                    self.controller = controller
            else:
                # From what I understand this will just get the spectro currently selected in the list
                dvc = self.settings.child('device').value()
                self.controller = Spectrometer(dvc)
                self.controller.open()
                #####################################

            # Oceanoptics spectrometers (at least the ones i Know) have fixed axis
            # get inactive pixels
            c0 = self.controller.f.spectrometer.get_electric_dark_pixel_indices()[-1]
            self.settings.child('advanced').child('dark_channels').setValue(c0)
            # get the x_axis
            data_x_axis = self.controller.wavelengths()  # Way to get the x axis
            data_x_axis = data_x_axis[c0:]  # Get rid of the dark pixels
            self.x_axis = Axis(data=data_x_axis, label='wavelength', units='nm')
            self.emit_x_axis()

            # Get the name
            specname = f"Ocean Insight {self.controller.model}"

            # initialize viewers pannel with the future type of data
            self.data_grabed_signal_temp.emit([
                DataFromPlugins(name=specname,
                                data=[np.zeros_like(data_x_axis)],
                                dim='Data1D',
                                labels=['Intensity'],
                                x_axis=self.x_axis), ])

            # Update the parameters
            # Here we need to do a few things. Get the integration time limits and set it in the settings
            tlimits = np.array(self.controller.integration_time_micros_limits) / 1000
            self.settings.child('integration').setLimits(tlimits)
            # Here we need to update the advanced parameters
            advanced_settings = self.settings.child('advanced')
            sn = self.controller.serial_number
            advanced_settings.child('serial_number').setValue(sn)
            # non linearity coefficients
            nlc_feat = self.controller.f.nonlinearity_coefficients
            if nlc_feat is not None and not any(np.isnan(nlc_feat.get_nonlinearity_coefficients())):
                advanced_settings.child('correct_non_linearity').setValue(True)
            else:
                advanced_settings.child('correct_non_linearity').setValue(False)
                advanced_settings.child('correct_non_linearity').setOpts(enabled=False)

            # measure the readout time
            Nperf = 200
            self.settings.child('integration').setValue(tlimits[0])  # Update the parameter value to the lower limit
            self.controller.integration_time_micros(tlimits[0]*1000)  # Set the readout time to lower limit
            perf = timeit(lambda: self.controller.intensities(), number=Nperf)  # time the execution of code in [s]
            self.settings.child('advanced').child('readout_time').setValue(1000*perf/Nperf)  # set the settings

            ##############################

            self.status.info = f"Initialized {specname} spectrometer"
            self.status.initialized = True
            self.status.controller = self.controller
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [getLineInfo() + str(e), 'log']))
            self.status.info = getLineInfo() + str(e)
            self.status.initialized = False
            return self.status

    def close(self):
        """
        Terminate the communication protocol
        """
        self.controller.close()
        ##

    def grab_data(self, Naverage = 1, **kwargs):
        """
        Parameters
        ----------
        Naverage: (int) Number of hardware averaging
        kwargs: (dict) of others optionals arguments
        """
        nlc = self.settings.child('advanced').child('correct_non_linearity').value()
        c0 = self.settings.child('advanced').child('dark_channels').value()
        # synchrone version (blocking function)
        # Pseudo-hardware-averaging
        if Naverage>1:
            data = [self.controller.intensities(correct_nonlinearity=nlc)[c0:] for i in range(Naverage)]
            data = np.array(data)
            data = data.mean(0)
        # Otherwise normal single-acquisition
        else:
            data = self.controller.intensities(correct_nonlinearity=nlc)[c0:]

        data_emit = DataFromPlugins(name='oceanseabreeze', data=[data], dim='Data1D', labels=['spectrum'])

        self.data_grabed_signal.emit([data_emit])
        #########################################################

    def callback(self):
        """optional asynchrone method called when the detector has finished its acquisition of data"""
        pass
        # data_tot = self.controller.your_method_to_get_data_from_buffer()
        # self.data_grabed_signal.emit([DataFromPlugins(name='Mock1', data=data_tot,
        #                                           dim='Data1D', labels=['dat0', 'data1'])])

    def stop(self):
        pass
        # self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))
        ##############################

if __name__ == '__main__':
    main(__file__)
