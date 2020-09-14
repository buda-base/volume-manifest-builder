from pathlib import Path

from ImageRepository.ImageRepositoryBase import ImageRepositoryBase
from VolumeInfo.VolumeInfoBase import VolInfo
from .ImageGroupResolver import ImageGroupResolver


class FSImageRepository(ImageRepositoryBase):

    def manifest_exists(self, *args) -> bool:
        complete_path: Path = self._IGResolver.full_path(work_Rid, vi.imageGroupID)


    def upload_manifest(self, *args):
        pass

    def generate_manifest(self, *args):
        global shell_logger
        if self.manifest_exists(complete_path):
            shell_logger.info(f"manifest exists: {complete_path}")
        pass

    def get_bom(self):
        pass

    def __init__(self, bom_key: str, source_root: str, images_name: str):
        """
        Creation.
        :param container: parent of all works in the repository. Existing directory name
        :param image_folder_name: subfolder of the work which contains the image group folders
        """
        super(FSImageRepository, self).__init__(bom_key)
        self._container = source_root
        self._image_folder_name = images_name
        self._IGResolver = ImageGroupResolver(source_root, images_name)