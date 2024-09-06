from urllib import request

from v_m_b.ImageRepository import ImageRepositoryBase
from v_m_b.VolumeInfo.VolumeInfoBase import VolumeInfoBase



# TODO: Extend to support a named image group
class VolumeInfoBUDA(VolumeInfoBase):
    """
    Gets the Volume list from BUDA. BUDA decided it did not want to support
    the get image list, so we have to turn to the repository provider to get the list from the VMT_BUDABOM
    """
    def __init__(self, repo: ImageRepositoryBase):
        super(VolumeInfoBUDA, self).__init__(repo)

    def get_image_group_disk_paths(self, work_rid: str) -> object:
        """
        BUDA LDS-PDI implementation
        :param: work_rid
        :return: VolInfo[]
        """

        from lxml import etree
        from archive_ops.api import get_disk_ig_from_buda
        vol_info = []

        req = f'http://purl.bdrc.io/query/table/volumesForInstance?R_RES=bdr:{work_rid}&format=xml'
        try:
            with request.urlopen(req) as response:
                rTree = etree.parse(response)
                rtRoot = rTree.getroot()

                # There's a lot of churn about namespaces and xml, including discussion of lxml vs xml,
                # but this works, using lxml
                # Thanks to: https://izziswift.com/parsing-xml-with-namespace-in-python-via-elementtree/
                for uri in rTree.findall('results/result/binding[@name="volid"]/uri',rtRoot.nsmap):
                    # the XML format returns the URI, not the bdr:Image group name, so that needs to be
                    # split out
                    uri_path:[] = uri.text.split(':')

                    # take the last thing
                    uri_path_nodes: str = uri_path[-1]

                    # find the last node on the path
                    image_group_name = uri_path_nodes.split('/')[-1]

                    vol_info.append(get_disk_ig_from_buda(image_group_name))
        # Swallow all exceptions.
        except Exception as eek:
            pass
        finally:
            pass

        return vol_info
