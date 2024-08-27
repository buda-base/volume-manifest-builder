# import os
# import ssl
from typing import List, Any
from urllib import request

import archive_ops.api

from v_m_b.ImageRepository import ImageRepositoryBase
from v_m_b.VolumeInfo.VolumeInfoBase import VolumeInfoBase


# TODO: Stop using
class VolumeInfoeXist(VolumeInfoBase):
    """
    this uses the exist db queries get the volume list of a work, including, for each volume:
    - image list
    - image group ID

    The information should be fetched (in csv or json) from lds-pdi, query for W22084 for instance is:
    http://www.tbrc.org/public?module=work&query=work-igs&arg=WorkRid
    """

    def __init__(self, repo: ImageRepositoryBase):
        super(VolumeInfoeXist, self).__init__(repo)

    def get_image_group_disk_paths(self, work_rid: str) -> []:
        """
        :param work_rid: Resource id
        :type work_rid: str
        """

        # Interesting first pass failure: @ urllib.error.URLError: <urlopen error
        # [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed (_ssl.c:777)>
        # # Tried fix
        # debugging lines needed on timb's machine also
        import os
        import ssl
        if not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None):
            ssl._create_default_https_context = ssl._create_unverified_context

        req = f'https://legacy.tbrc.org/public?module=work&query=work-igs&args={work_rid}'

        vol_info: List[Any] = []
        from lxml import etree

        try:

            with request.urlopen(req) as response:
                info = response.read()
                info = info.decode('utf8').strip()

                # work-igs returns one node with space delimited list of image groups
                rTree = etree.fromstring(info)
                ig_text = rTree.text
                if ig_text:
                    igs = ig_text.split(" ")
                    for ig in ig_text:
                        vol_info.append(archive_ops.api.get_disk_ig_from_buda(ig))
        except etree.ParseError:
            pass
        return vol_info


