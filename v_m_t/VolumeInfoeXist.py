from typing import List, Any
from urllib import request

from v_m_t.VolumeInfoBase import VolumeInfoBase, VolInfo


class VolumeInfoeXist(VolumeInfoBase):
    """
    this uses the exist db queries get the volume list of a work, including, for each volume:
    - image list
    - image group ID

    The information should be fetched (in csv or json) from lds-pdi, query for W22084 for instance is:
    http://www.tbrc.org/public?module=work&query=work-igs&arg=WorkRid
    """

    def fetch(self, work_rid: str) -> []:
        """
        :param work_rid: Resource id
        :type work_rid: object
        """

        # Interesting first pass failure: @ urllib.error.URLError: <urlopen error
        # [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed (_ssl.c:777)>
        # # Tried fix
        req = f'http://www.tbrc.org/public?module=work&query=work-igs&args={work_rid}'

        vol_info: List[Any] = []
        from lxml import etree

        try:

            with request.urlopen(req) as response:
                info = response.read()
                info = info.decode('utf8').strip()

                # work-igs returns one node with space delimited list of image groups
                igs: str = etree.fromstring(info).text.split(" ")
                vol_info = self.expand_groups(work_rid, igs)
        except etree.ParseError:
            pass

        return vol_info

    def expand_groups(self, work_rid: str, image_groups: []) -> object:
        """
        expands an image group into a list of its files
        :type image_groups: []
        :param work_rid: work resource Id
        :param image_groups: Image Groups to expand
        :return: VolInfo[] of all the images in all imagegroups in the input
        """
        vi = []
        for ig in image_groups:
            vol_infos = self.get_image_names_from_S3(work_rid, ig)
            vi.append(VolInfo(vol_infos, ig))

        return vi
