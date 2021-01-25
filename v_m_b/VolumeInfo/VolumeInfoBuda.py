from urllib import request

from v_m_b.ImageRepository import ImageRepositoryBase
from v_m_b.VolumeInfo.VolumeInfoBase import VolumeInfoBase
from v_m_b.VolumeInfo.VolInfo import VolInfo


def expand_image_list(image_list_str: str) -> []:
    """
    expands an image list string into an array. Image lists are documented on
     http://purl.bdrc.io/ontology/core/imageList
    see also this example in Java (although probably a bit too sophisticated):
    https://github.com/buda-base/buda-iiif-presentation/blob
    /d64a2c47c056bfa8658c06c1cddd2566ff4a0a2a/src/main/java/io/bdrc/
    iiif/presentation/models/ImageListIterator.java
    Example:
       - image_list_str="I2PD44320001.tif:2|I2PD44320003.jpg"
       - result ["I2PD44320001.tif","I2PD44320002.tif","I2PD44320003.jpg"]

    :param image_list_str: encoded image list Filenameroot.ext:n|....
    :return: list of strings which expands the encoded list of names
    """
    image_list = []
    spans = image_list_str.split('|')
    for s in spans:
        if ':' in s:
            name, count = s.split(':')
            dot = name.find('.')
            prefix, num, ext = name[:dot - 4], name[dot - 4:dot], name[dot:]
            for i in range(int(count)):
                incremented = str(int(num) + i).zfill(len(num))
                image_list.append('{}{}{}'.format(prefix, incremented, ext))
        else:

            # jimk. #10  Don't add emptiness
            if len(s) > 0:
                image_list.append(s)

    return image_list


class VolumeInfoBUDA(VolumeInfoBase):
    """
    this uses the LDS-PDI capabilities to get the volume list of a work, including, for each volume:
    - image list
    - image group ID

    The information should be fetched (in csv or json) from lds-pdi, query for W00EGS1016299 for instance is:
    http://purl.bdrc.io/query/Work_ImgList?R_RES=bdr:W00EGS1016299&format=csv&profile=simple&pageSize=500
    item,list,grId
    bdr:I00EGS1016299,,I1CZ5001
    bdr:I00EGS101629,I1CZ50020001.tif:1266,I1CZ5002
    bdr:I00EGS1016299,I1CZ50030001.tif:1136,I1CZ5003
    bdr:I00EGS1016299,I1CZ50040001.tif:1276,I1CZ5004
    bdr:I00EGS1016299,I1CZ50050001.tif:928,I1CZ5005
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

        # TODO: If we ever get this working again, good to document the output format
        req = f'http://purl.bdrc.io/query/table/Work_ImgList?R_RES=bdr:{_work}' \
              '&format=csv&profile=simple&pageSize=500'
        try:
            with request.urlopen(req) as response:
                _info = response.read()
                info = _info.decode('utf8').strip()
                lines = info.split('\n')[1:]
                for line in lines:  # info.split('\n')[1:]:
                    # appears each line contains:
                    # _  an ignored variable
                    #  l an encoded list of images
                    #  g the image group
                    _, l, g = line.replace('"', '').split(',')
                    #
                    # jimk: mod: redefine volInfo to expand list here, rather than just before processing.
                    image_list = expand_image_list(l)

                    # This is the case when the image list processing has broken or is not
                    # # available. Fallback to slicing the image groups vertically
                    if len(image_list) == 0:
                        image_list = self.getImageNames(work_rid, g)

                    # Dont add empty vol infos
                    if len(image_list) > 0:
                        vi = VolInfo(image_list, g)
                        # This is an interim hack to compensate for BUDA not having the information we need
                        vol_info.append(vi)
                    else:
                        self.logger.warn(f"No images found in group {g}")
        # Swallow all exceptions.
        except Exception as eek:
            pass
        finally:
            pass

        return vol_info
