import csv
from urllib import request

from v_m_b.ImageRepository import ImageRepositoryBase
from v_m_b.VolumeInfo.VolumeInfoBase import VolumeInfoBase
from v_m_b.VolumeInfo.VolInfo import VolInfo
from v_m_b.manifestCommons import VMT_BUDABOM

class VolumeInfoBUDA(VolumeInfoBase):
    """
    Gets the Volume list from BUDA. BUDA decided it did not want to support
    the get image list, so we have to turn to the repository provider to get the list from the VMT_BUDABOM
    """
    def __init__(self, repo: ImageRepositoryBase):
        super(VolumeInfoBUDA, self).__init__(repo)

    def fetch(self, work_rid: str) -> object:
        """
        BUDA LDS-PDI implementation
        :param: work_rid
        :return: VolInfo[]
        """
        vol_info = []

        _dir, _work = self._repo.resolveWork(work_rid)

        req= f'http://purl.bdrc.io/query/table/volumesForInstance?R_RES=bdr:{_work}&format=csv'
        try:
            with request.urlopen(req) as response:
                _info = response.read()
                info = _info.decode('utf8').strip()
                vol_list_reader = csv.reader(info.split('\n'))

                # skip header
                next(vol_list_reader)
                for vol_list in vol_list_reader:  # info.split('\n')[1:]:
                    # jimk: mod: redefine volInfo to expand list here, rather than just before processing.
                    # vol_list = ["1","bdr:I1Whatever"]
                    image_group_name = vol_list[1].split(':')[1]

                    # HACK
                    image_group_folder = self.getImageGroup(image_group_name)
                    image_list = self.getImageNames(work_rid, image_group_folder, VMT_BUDABOM)

                    # Dont add empty vol infos
                    if len(image_list) > 0:
                        vi = VolInfo(image_list, image_group_folder)
                        vol_info.append(vi)
                    else:
                        self.logger.warn(f"No images found in group named {image_group_name} folder {image_group_folder}")
        # Swallow all exceptions.
        except Exception as eek:
            pass
        finally:
            pass

        return vol_info
