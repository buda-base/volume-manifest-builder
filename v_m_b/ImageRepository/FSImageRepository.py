import os
import sys
from pathlib import Path, PurePath

import aiofiles

from ImageRepository.ImageRepositoryBase import ImageRepositoryBase
from VolumeInfo.VolInfo import VolInfo
from .ImageGroupResolver import ImageGroupResolver
from v_m_b.manifestCommons import fillDataWithBlobImage


class FSImageRepository(ImageRepositoryBase):

    def manifest_exists(self, work_Rid: str, image_group_id: str) -> bool:
        """
        tests for a well known item in the repository
        :param work_Rid:
        :param image_group_id:
        :return:
        """
        return Path(self._IGResolver.full_path(work_Rid, image_group_id), 'dimensions.json').exists()

    def upload_manifest(self, *args):
        pass

    def generateManifest(self, work_Rid: str, vol_info: VolInfo) -> []:
        if self.manifest_exists(work_Rid, vol_info.imageGroupID):
            self.repo_log.info(f"manifest exists for work{work_Rid} image group {vol_info.imageGroupID}")
        import asyncio
        full_path: Path = self._IGResolver.full_path(work_Rid, vol_info.imageGroupID)
        asyncio.run(generateManifest_a(full_path, vol_info.image_list))

    def get_bom(self):
        pass

    def __init__(self, bom_key: str, source_root: str, images_name: str):
        """
        Creation.
        :param source_root: parent of all works in the repository. Existing directory name
        :param images_name: subfolder of the work which contains the image group folders
        """
        super(FSImageRepository, self).__init__(bom_key)
        self._container = source_root
        self._image_folder_name = images_name
        self._IGResolver = ImageGroupResolver(source_root, images_name)

    def getImageNames(self, work_rid: str, image_group: str, bom_name: str) -> []:

        # try reading the bom first
        bom_home = Path(self._IGResolver.full_path(work_rid, image_group))
        bom_path = Path(bom_home, bom_name)

        if bom_path.exists():
            with str(bom_path) as f:
                image_list = [i for i in f.readlines()]
            if len(image_list) > 0:
                return image_list
        else:
            return [f for f in os.listdir('.') if os.path.isfile(f) and not str(f).lower().endswith('json')]


# downloading region
async def generateManifest_a(ig_container: PurePath, image_list: []) -> []:
    """
    this actually generates the manifest. See example in the repo. The example corresponds to W22084, image group I0886.
    :param ig_container: path of parent of image group
    :param image_list: list of image names
    :returns: list of  internal data for each file in image_list
    """

    res = []

    image_file_name: str
    for image_file_name in image_list:
        image_path: Path = Path(ig_container, image_file_name)
        imgdata = {"filename": image_file_name}
        res.append(imgdata)
        # extracted from fillData
        async with aiofiles.open(image_path, "rb") as image_file:
            image_buffer = await image_file.read()
            # image_buffer = io.BytesIO(image_file.read())
            try:
                fillDataWithBlobImage(image_buffer, imgdata)
            except Exception as eek:
                exc = sys.exc_info()
                print(eek, exc[0])
        # asyncio.run(fillData(image_path, imgdata))
    return res


def generateManifest_s(ig_container: PurePath, image_list: []) -> []:
    """
    this actually generates the manifest. See example in the repo. The example corresponds to W22084, image group I0886.
    :param ig_container: path of parent of image group
    :param image_list: list of image names
    :returns: list of  internal data for each file in image_list
    """

    res = []

    image_file_name: str
    for image_file_name in image_list:
        image_path: Path = Path(ig_container, image_file_name)
        imgdata = {"filename": image_file_name}
        res.append(imgdata)
        # extracted from fillData
        with open(str(image_path), "rb") as image_file:
            image_buffer = image_file.read()
            # image_buffer = io.BytesIO(image_file.read())
            try:
                fillDataWithBlobImage(image_buffer, imgdata)
            except Exception as eek:
                exc = sys.exc_info()
                print(eek, exc[0])
        # asyncio.run(fillData(image_path, imgdata))
    return res
# end region
