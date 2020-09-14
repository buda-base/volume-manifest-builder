"""
Base class for image repositories
"""

from abc import ABCMeta, abstractmethod

from VolumeInfo.VolumeInfoBase import VolInfo
import logging


class ImageRepositoryBase(metaclass=ABCMeta):

    @abstractmethod
    def manifest_exists(self, *args) -> bool:
        """
        Test if a manifest exists
        :param args: implementation dependent
        :return: true if the args point to a path containing a 'dimensions.json' object
        """
        pass

    @abstractmethod
    def upload_manifest(self, *args):
        pass

    @abstractmethod
    def generate_manifest(self, *args):
        pass

    @abstractmethod
    def get_bom(self):
        """
        Get the bill of materials for the image group - an object named 'fileList.json'
        :return:
        """
        pass

    # RO property
    @property
    def repo_log(self) -> object:
        return self._log

    @property
    def BOM(self) -> str:
        return self._bom

    @BOM.setter
    def BOM(self, value: str):
        self._bom = value

    def __init__(self, bom: str) -> object:
        """
        :param bom: key to bill of materials
        :type bom: str
        """
        self._bom = bom
        self._log = logging.getLogger(__name__)
