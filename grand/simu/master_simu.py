"""

"""
import os
import os.path
from logging import getLogger
import time
import numpy as np

import grand.geo.coordinates as coord
from grand.simu.du.process_ant import AntennaProcessing
from grand.simu.shower.gen_shower import ShowerEvent
from grand.io.root_file import FileSimuEfield
from grand.simu.du.model_ant_du import AntennaModelGp300
from grand.basis.type_trace import ElectricField
from grand.basis.traces_event import HandlingTracesOfEvent
from grand.io.root_trees import VoltageEventTree


logger = getLogger(__name__)


class MasterSimuDetectorWithRootIo(object):
    def __init__(self, f_name_root):
        self.f_name_root = f_name_root
        self.d_root = FileSimuEfield(f_name_root)
        self.simu_du = SimuDetectorUnitEffect()
        

    def _load_data_to_process_event(self, idx):
        logger.info(f"Compute du simulation for traces of event idx= {idx}")
        self.d_root.load_event_idx(idx)
        self.tr_evt = self.d_root.get_obj_handlingtracesofevent()
        # for debug
        self.tr_evt.reduce_nb_du(12)
        assert isinstance(self.tr_evt, HandlingTracesOfEvent)
        self.simu_du.set_data_efield(self.tr_evt)
        shower = ShowerEvent()
        shower.load_root(self.d_root.tt_shower)
        self.simu_du.set_data_shower(shower)

    def compute_event_du_idx(self, idx_evt, idx_du):
        self._load_data_to_process_event(idx_evt)
        return self.simu_du.compute_du_idx(idx_du)

    def compute_event_idx(self, idx):
        self._load_data_to_process_event(idx)
        return self.simu_du.compute_du_all()

    def save_voltage(self, file_out="", append_file=True):
        self.tt_voltage = VoltageEventTree()
        # delete file can be take time => start with this action
        if file_out == "":
            file_out = self.f_name_root
        if not append_file and os.path.exists(file_out):
            logger.info(f"save on new file option => remove file {file_out}")
            os.remove(file_out)
            time.sleep(1)
        # now fill Voltage object
        # freq_mhz = int(self.d_root.get_sampling_freq_mhz())
        # self.tt_voltage.du_count = self.tr_evt.get_nb_du()
        logger.debug(f"We will add {self.tt_voltage.du_count} DU")
        logger.debug(f"We will add {self.tt_voltage.du_count} DU")
        self.tt_voltage.run_number = 0  # self.d_root.tt_efield.run_number
        self.tt_voltage.event_number = 0  # self.d_root.tt_efield.event_number
        logger.info(f"{type(self.tt_voltage.run_number)} {type(self.tt_voltage.event_number)}")
        logger.info(f"{self.tt_voltage.run_number} {self.tt_voltage.event_number}")
        # self.tt_voltage.first_du = self.tr_evt.du_id[0]
        # self.tt_voltage.time_seconds = 0 #self.d_root.tt_efield.time_seconds
        # self.tt_voltage.time_nanoseconds = 0 #self.d_root.tt_efield.time_nanoseconds
        # self.tr_evt.traces = self.simu_du.voc
        # self.tr_evt.define_t_samples()
        self.tt_voltage.event_size = 1999
        for idx in range(10):
            trace = np.arange(self.tt_voltage.event_size, dtype=np.float64)
            # self.tr_evt.plot_trace_idx(idx)
            # logger.info(f'add DU {self.tr_evt.du_id[idx]} in ROOT file')
            # logger.info(f'shape: {self.simu_du.voc[idx, 0].shape}')
            # self.tt_voltage.du_nanoseconds.append(self.d_root.tt_efield.du_nanoseconds[idx])
            # self.tt_voltage.du_seconds.append(self.d_root.tt_efield.du_seconds[idx])
            # self.tt_voltage.adc_sampling_frequency.append(freq_mhz)
            # self.tt_voltage.du_id.append(int(self.tr_evt.du_id[idx]))
            # logger.info(f'du_id {type(self.tr_evt.du_id[idx])}')
            # self.tt_voltage.trace_x.append(self.simu_du.voc[idx, 0].astype(np.float64).tolist())
            # logger.info(f'Trace {trace.shape} {trace.dtype}')
            # trace = self.simu_du.voc[idx, 0].astype(np.float64)
            # logger.info(f'Trace {trace.shape} {trace.dtype}')
            self.tt_voltage.trace_x.append(trace.tolist())
            self.tt_voltage.trace_z.append(trace.tolist())
            self.tt_voltage.trace_z.append(trace.tolist())
            # logger.info(f'{self.simu_du.voc[idx, 0][:10]}')
            # logger.info(f'{self.tt_voltage.trace_x[-1][:10]}')
            # self.tt_voltage.trace_y.append(self.simu_du.voc[idx, 1].astype(np.float64).tolist())
            # self.tt_voltage.trace_z.append(self.simu_du.voc[idx, 2].astype(np.float64).tolist())
        # logger.info(f'{self.tt_voltage.du_id}')
        ret = self.tt_voltage.fill()
        # logger.debug(ret)
        ret = self.tt_voltage.write(file_out)
        # logger.debug(self.tt_voltage)

    def compute_event_all(self):
        nb_events = self.d_root.get_nb_events()
        for idx in range(nb_events):
            self.compute_event(idx)


class SimuDetectorUnitEffect(object):
    """
    Simulate detector effect only on one event, IO data file free

    Adaption of RF simulation chain for grandlib from
      * https://github.com/JuliusErv1ng/XDU-RF-chain-simulation/blob/main/XDU%20RF%20chain%20code.py
    """

    def __init__(self):
        """
        Constructor
        """
        self.t_samp = 0.5  # Manually enter the same time interval as the .trace file
        self.show_flag = False
        self.noise_flag = False
        self.ant_model = AntennaModelGp300()
        self.voc = None

    ### INTERNAL
    def _get_ant_leff(self, idx_du):
        """
        Define for each antenna in DU idx_du an object AntennaProcessing according its position

        :param idx_du:
        """
        antenna_location = coord.LTP(
            x=self.du_pos[idx_du, 0],
            y=self.du_pos[idx_du, 1],
            z=self.du_pos[idx_du, 2],
            frame=self.o_shower.frame,
        )
        logger.debug(antenna_location)
        antenna_frame = coord.LTP(location=antenna_location, orientation="NWU", magnetic=True)
        self.ant_leff_sn = AntennaProcessing(model_leff=self.ant_model.leff_sn, frame=antenna_frame)
        self.ant_leff_ew = AntennaProcessing(model_leff=self.ant_model.leff_ew, frame=antenna_frame)
        self.ant_leff_z = AntennaProcessing(model_leff=self.ant_model.leff_z, frame=antenna_frame)

    ### SETTER

    def set_data_efield(self, tr_evt):
        assert isinstance(tr_evt, HandlingTracesOfEvent)
        self.tr_evt = tr_evt
        tr_evt.define_t_samples()
        self.du_time_efield = tr_evt.t_samples
        self.du_efield = tr_evt.traces
        self.du_pos = tr_evt.network.du_pos
        self.du_id = tr_evt.du_id
        self.voc = np.zeros_like(self.du_efield)

    def set_data_shower(self, shower):
        assert isinstance(shower, ShowerEvent)
        self.o_shower = shower

    ### GETTER / COMPUTER

    def compute_du_all(self):
        nb_du = self.du_efield.shape[0]
        for idx in range(nb_du):
            self.compute_du_idx(idx)
            # store result

    def compute_du_idx(self, idx_du):
        """ """
        logger.info(f"==============>  Processing DU with id: {self.du_id[idx_du]}")
        self._get_ant_leff(idx_du)
        logger.debug(self.ant_leff_sn.model_leff)
        # define E field at antenna position
        d_efield = coord.CartesianRepresentation(
            x=self.du_efield[idx_du, 0], y=self.du_efield[idx_du, 1], z=self.du_efield[idx_du, 2]
        )
        self.o_efield = ElectricField(self.du_time_efield[idx_du] * 1e-9, d_efield)
        # compute 3 axis
        self.voc[idx_du, 0] = self.ant_leff_sn.compute_voltage(
            self.o_shower.maximum, self.o_efield, self.o_shower.frame
        ).V
        self.voc[idx_du, 1] = self.ant_leff_ew.compute_voltage(
            self.o_shower.maximum, self.o_efield, self.o_shower.frame
        ).V
        self.voc[idx_du, 2] = self.ant_leff_z.compute_voltage(
            self.o_shower.maximum, self.o_efield, self.o_shower.frame
        ).V
