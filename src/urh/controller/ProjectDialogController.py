import os
import random

import numpy
from PyQt5.QtCore import pyqtSlot, QAbstractTableModel, Qt, QModelIndex
from PyQt5.QtWidgets import QDialog, QCompleter, QDirModel, QTableWidgetItem
from urh import constants

from urh.controller.SendRecvDialogController import SendRecvDialogController
from urh.dev.VirtualDevice import Mode
from urh.signalprocessing.Participant import Participant
from urh.ui.delegates.ComboBoxDelegate import ComboBoxDelegate
from urh.ui.ui_project import Ui_ProjectDialog
from urh.util import FileOperator
from urh.util.Errors import Errors

import string

from urh.util.ProjectManager import ProjectManager


class ProjectDialogController(QDialog):
    class ProtocolParticipantModel(QAbstractTableModel):
        def __init__(self, participants):
            super().__init__()
            self.participants = participants
            self.header_labels = ["Name", "Shortname", "Color", "Address (hex)"]

        def update(self):
            self.layoutChanged.emit()

        def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
            return len(self.header_labels)

        def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
            return len(self.participants)

        def headerData(self, section, orientation, role=Qt.DisplayRole):
            if role == Qt.DisplayRole and orientation == Qt.Horizontal:
                return self.header_labels[section]
            return super().headerData(section, orientation, role)

        def data(self, index: QModelIndex, role=Qt.DisplayRole):
            if role == Qt.DisplayRole:
                i = index.row()
                j = index.column()
                part = self.participants[i]
                if j == 0:
                    return part.name
                elif j == 1:
                    return part.shortname
                elif j == 2:
                    return part.color_index
                elif j == 3:
                    return part.address_hex

        def setData(self, index: QModelIndex, value, role=Qt.DisplayRole):
            i = index.row()
            j = index.column()
            if i >= len(self.participants):
                return False

            parti = self.participants[i]

            if j == 0:
                parti.name = value
            elif j == 1:
                parti.shortname = value
            elif j == 2:
                parti.color_index = int(value)
            elif j == 3:
                parti.address_hex = value

            return True

        def flags(self, index: QModelIndex):
            if not index.isValid():
                return Qt.NoItemFlags

            return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def __init__(self, new_project=True, project_manager:ProjectManager=None, parent=None):
        super().__init__(parent)
        if not new_project:
            assert  project_manager is not None

        self.ui = Ui_ProjectDialog()
        self.ui.setupUi(self)

        if new_project:
            self.parti_table_model = self.ProtocolParticipantModel([])
        else:
            self.parti_table_model = self.ProtocolParticipantModel(project_manager.participants)

            self.ui.spinBoxSampleRate.setValue(project_manager.sample_rate)
            self.ui.spinBoxFreq.setValue(project_manager.frequency)
            self.ui.spinBoxBandwidth.setValue(project_manager.bandwidth)
            self.ui.spinBoxGain.setValue(project_manager.gain)
            self.ui.txtEdDescription.setPlainText(project_manager.description)
            self.ui.lineEdit_Path.setText(project_manager.project_path)

            self.ui.btnSelectPath.hide()
            self.ui.lineEdit_Path.setDisabled(True)
            self.setWindowTitle("Edit project settings")
            self.ui.lNewProject.setText("Edit project")
            self.ui.btnOK.setText("Accept")

        self.ui.tblParticipants.setModel(self.parti_table_model)
        self.ui.tblParticipants.setItemDelegateForColumn(2, ComboBoxDelegate([""] * len(constants.PARTICIPANT_COLORS),
                                                                            colors=constants.PARTICIPANT_COLORS,
                                                                            parent=self))



        self.sample_rate = self.ui.spinBoxSampleRate.value()
        self.freq = self.ui.spinBoxFreq.value()
        self.bandwidth = self.ui.spinBoxBandwidth.value()
        self.gain = self.ui.spinBoxGain.value()
        self.description = self.ui.txtEdDescription.toPlainText()

        self.ui.btnRemoveParticipant.setDisabled(len(self.participants) <= 1)

        self.path = self.ui.lineEdit_Path.text()
        self.new_project = new_project
        self.commited = False
        self.setModal(True)

        completer = QCompleter()
        completer.setModel(QDirModel(completer))
        self.ui.lineEdit_Path.setCompleter(completer)

        self.create_connects()

        if new_project:
            self.ui.lineEdit_Path.setText(os.path.realpath(os.path.join(os.curdir, "new")))

        self.on_path_edited()

        self.open_editors()

    @property
    def participants(self):
        """

        :rtype: list of Participant
        """
        return self.parti_table_model.participants

    def create_connects(self):
        self.ui.spinBoxFreq.valueChanged.connect(self.on_frequency_changed)
        self.ui.spinBoxSampleRate.valueChanged.connect(self.on_sample_rate_changed)
        self.ui.spinBoxBandwidth.valueChanged.connect(self.on_bandwidth_changed)
        self.ui.spinBoxGain.valueChanged.connect(self.on_gain_changed)
        self.ui.txtEdDescription.textChanged.connect(self.on_description_changed)

        self.ui.btnAddParticipant.clicked.connect(self.on_btn_add_participant_clicked)
        self.ui.btnRemoveParticipant.clicked.connect(self.on_btn_remove_participant_clicked)

        self.ui.lineEdit_Path.textEdited.connect(self.on_path_edited)
        self.ui.btnOK.clicked.connect(self.on_button_ok_clicked)
        self.ui.btnSelectPath.clicked.connect(self.on_btn_select_path_clicked)
        self.ui.lOpenSpectrumAnalyzer.linkActivated.connect(self.on_spectrum_analyzer_link_activated)

    def on_sample_rate_changed(self):
        self.sample_rate = self.ui.spinBoxSampleRate.value()

    def on_frequency_changed(self):
        self.freq = self.ui.spinBoxFreq.value()

    def on_bandwidth_changed(self):
        self.bandwidth = self.ui.spinBoxBandwidth.value()

    def on_gain_changed(self):
        self.gain = self.ui.spinBoxGain.value()

    def on_path_edited(self):
        self.set_path(self.ui.lineEdit_Path.text())

    def on_description_changed(self):
        self.description = self.ui.txtEdDescription.toPlainText()

    def on_button_ok_clicked(self):
        self.path = os.path.realpath(self.path)
        if not os.path.exists(self.path):
            try:
                os.makedirs(self.path)
            except Exception:
                pass

        # Path should be created now, if not raise Error
        if not os.path.exists(self.path):
            Errors.invalid_path(self.path)
            return

        self.commited = True
        self.close()

    def set_path(self, path):
        self.path = path
        self.ui.lineEdit_Path.setText(self.path)
        name = os.path.basename(os.path.normpath(self.path))
        self.ui.lblName.setText(name)

        self.ui.lblNewPath.setVisible(not os.path.isdir(self.path))

    def on_btn_select_path_clicked(self):
        directory = FileOperator.get_directory()
        if directory:
            self.set_path(directory)

    @pyqtSlot(str)
    def on_spectrum_analyzer_link_activated(self, link: str):
        if link == "open_spectrum_analyzer":
            r = SendRecvDialogController(433.92e6, 1e6, 1e6, 20, "", Mode.spectrum, parent=self)
            if r.has_empty_device_list:
                Errors.no_device()
                r.close()
                return

            r.recording_parameters.connect(self.set_params_from_spectrum_analyzer)
            r.show()

    def set_params_from_spectrum_analyzer(self, freq: str, sample_rate: str, bw: str, gain: str, dev_name: str):
       self.ui.spinBoxFreq.setValue(float(freq))
       self.ui.spinBoxSampleRate.setValue(float(sample_rate))
       self.ui.spinBoxBandwidth.setValue(float(bw))
       self.ui.spinBoxGain.setValue(int(gain))


    def on_btn_add_participant_clicked(self):
        used_shortnames = {p.shortname for p in self.participants}
        used_colors = set(p.color_index for p in self.participants)
        avail_colors = set(range(0, len(constants.PARTICIPANT_COLORS))) - used_colors
        if len(avail_colors) > 0:
            color_index = avail_colors.pop()
        else:
            color_index = random.choice(range(len(constants.PARTICIPANT_COLORS)))

        nchars = 0
        participant = None
        while participant is None:
            nchars += 1
            for c in string.ascii_uppercase:
                shortname = nchars * str(c)
                if shortname not in used_shortnames:
                    participant = Participant("Device "+shortname, shortname=shortname, color_index=color_index)
                    break

        self.participants.append(participant)
        self.parti_table_model.update()
        self.ui.btnRemoveParticipant.setEnabled(True)
        self.open_editors()

    def on_btn_remove_participant_clicked(self):
        if len(self.participants) <= 1:
            return

        selected = self.ui.tblParticipants.selectionModel().selection()
        if selected.isEmpty():
            start, end = len(self.participants) - 1, len(self.participants) - 1  # delete last element
        else:
            start, end = numpy.min([rng.top() for rng in selected]), numpy.max([rng.bottom() for rng in selected])

        if end - start >= len(self.participants) - 1:
            # Ensure one left
            start += 1

        del self.participants[start:end+1]
        self.parti_table_model.update()
        self.ui.btnRemoveParticipant.setDisabled(len(self.participants) <= 1)
        self.open_editors()

    def open_editors(self):
        for row in range(len(self.participants)):
            self.ui.tblParticipants.openPersistentEditor(self.parti_table_model.index(row, 2))
