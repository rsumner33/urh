import random
import string
from copy import deepcopy

from urh import constants
from urh.signalprocessing.ProtocoLabel import ProtocolLabel
from urh.util.Logger import logger
import xml.etree.ElementTree as ET

class LabelSet(list):
    def __init__(self, name: str, iterable=None, id=None):
        iterable = iterable if iterable else []
        super().__init__(iterable)

        self.name = name
        self.__id = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(50)) if id is None else id


    @property
    def id(self) -> str:
        return self.__id

    def append(self, lbl: ProtocolLabel):
        super().append(lbl)

    def add_protocol_label(self, start: int, end: int, type_index: int, name=None, color_ind=None) -> \
            ProtocolLabel:

        name = "Label {0:d}".format(len(self) + 1) if not name else name
        used_colors = [p.color_index for p in self]
        avail_colors = [i for i, _ in enumerate(constants.LABEL_COLORS) if i not in used_colors]

        if color_ind is None:
            if len(avail_colors) > 0:
                color_ind = avail_colors[random.randint(0, len(avail_colors) - 1)]
            else:
                color_ind = random.randint(0, len(constants.LABEL_COLORS) - 1)

        proto_label = ProtocolLabel(name=name, start=start, end=end, val_type_index=type_index, color_index=color_ind)

        if proto_label not in self:
            self.append(proto_label)
            self.sort()

        return proto_label # Return label to set editor focus after adding

    def add_label(self, lbl: ProtocolLabel):
        self.add_protocol_label(lbl.start, lbl.end, type_index=0, name=lbl.name, color_ind=lbl.color_index)

    def remove(self, lbl: ProtocolLabel):
        if lbl in self:
            super().remove(lbl)
        else:
            logger.warning(lbl.name + " is not in set, so cant be removed")

    def __getitem__(self, index) -> ProtocolLabel:
        return super().__getitem__(index)

    def to_xml(self) -> ET.Element:
        result = ET.Element("labelset", attrib={"name": self.name, "id": self.id})
        for lbl in self:
            result.append(lbl.to_xml(-1))
        return result

    def copy_for_fuzzing(self):
        result = deepcopy(self)
        for lbl in result:
            lbl.fuzz_values = []
            lbl.fuzz_created = True
        return result

    def __repr__(self):
        return self.name + " " + super().__repr__()

    def __eq__(self, other):
        if isinstance(other, LabelSet):
            return self.id == other.id
        else:
            return super().__eq__(other)

    @staticmethod
    def from_xml(tag:  ET.Element):
        name = tag.get("name", "blank")
        id = tag.get("id", None)
        labels = []
        for lbl_tag in tag.findall("label"):
            labels.append(ProtocolLabel.from_xml(lbl_tag))
        return LabelSet(name=name, iterable=labels, id=id)