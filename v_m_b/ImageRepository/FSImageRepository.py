import asyncio
import json
import os
from pathlib import Path
from typing import Tuple
from util_lib.utils import reallypath


import v_m_b.manifestCommons as Common
from v_m_b.ImageRepository.ImageRepositoryBase import ImageRepositoryBase
# You only use onf generateManifest_a or _s
from v_m_b.image.generateManifest import generateManifest_s, generateManifest_a


class FSImageRepository(ImageRepositoryBase):


    def generateManifest(self, work_Rid: str, vol_info: str) -> []:
        full_path: Path = self.resolve_image_group(work_Rid, vol_info)

        # if there's an existing output, flag it
        if os.path.exists(full_path / Common.VMT_DIM):
            self.repo_log.info(f"manifest exists for work {work_Rid} image group {vol_info}")
        manifest: [] = []
        if full_path.exists():
            manifest = asyncio.run(generateManifest_a(full_path),)
            # manifest = generateManifest_s(full_path)
        else:
            self.repo_log.error(f"image group path {str(full_path)} not found")
        return self.clean_manifest(manifest)

    def __init__(self, source_root: str, images_name: str):
        """
        Creation.
        :param source_root: parent of all works in the repository. Existing directory name
        :param images_name: subfolder of the work which contains the image group folders
        """
        super(FSImageRepository, self).__init__(images_name)
        # This insures _container is always absolute. You need this so that
        # you can pass a path in the --work-rid argument
        self._container = reallypath(source_root)
        self._image_folder_name = images_name
#        self._IGResolver = ImageGroupResolver(source_root, images_name)


    def uploadManifest(self, work_rid: str, image_group: str, bom_name: str, manifest_zip: bytes):
        """
        FS implemenation
        :param work_rid:
        :param image_group:
        :param bom_name: output object name
        :param manifest_zip:
        :return:
        """
        bom_path = Path(self.resolve_image_group(work_rid, image_group), bom_name)
        with open(bom_path, "wb") as upl:
            upl.write(manifest_zip)

    def resolve_image_group(self, work_rid: str, image_group_disk: str) -> Path:
        """
        Fully qualifies a RID and a Path
        :param work_rid:
        :param image_group_disk: Image group folder name
        :return: fully qualified path to image group on disk.
        """
        _dir, _work_rid = self.resolve_work(work_rid)
        return Path(reallypath(self._container),
                    _dir, _work_rid, self.images_folder_name,
                    f"{_work_rid}-{image_group_disk}")

    def manifest_exists(self, work_Rid: str, image_group_name: str) -> bool:
        dims_path: Path =  Path(self.resolve_image_group(work_Rid, image_group_name), Common.VMT_DIM)
        return dims_path.exists()

    def resolve_work(self, work_rid: str) -> (object, str):
        """
        Resolve a work RID to a path and identifier
        :param work_rid: work identifier
        :return: path to the work
        """
        _p: Path =  Path(reallypath(self._container), work_rid)
        return _p.parent, _p.name
