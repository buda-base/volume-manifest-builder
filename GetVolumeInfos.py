import abc
import collections
from urllib import request

from boto3 import client
from botocore.paginate import Paginator

import getS3FolderPrefix

VolInfo = collections.namedtuple('VolInfo', ['imageList', 'imageGroupID'])


class GetVolumeInfoBase(metaclass=abc.ABCMeta):
    """
    Gets volume info for a work.
    Passes request off to subclasses
    """

    boto_client: client = None

    # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/paginators.html
    boto_paginator: Paginator = None

    def __init__(self, boto_client: client):
        """
        :param boto_client: context for operations
        :type boto_client: boto3.client
        """
        self.boto_client = boto_client
        self.boto_paginator = self.boto_client.get_paginator('list_objects_v2')

    @abc.abstractmethod
    def fetch(self, urlRequest) -> []:
        """
        Subclasses implement
        :param urlRequest:
        :return: VolInfo[] with  one entry for each image in the image group
        """
        pass

    def get_image_names(self, work_rid: str, image_group: str) -> []:
        """
        get names of the image files (actually, all the files in an image group, regardless
        :type image_group: str
        :param work_rid:
        :param image_group:
        :return: str[]
        """

        image_list = []
        full_image_group_path: str = getS3FolderPrefix.getS3FolderPrefix(work_rid, image_group)
        page_iterator = self.boto_paginator.paginate(Bucket=f"archive.tbrc.org", Prefix=full_image_group_path)

        # #10 filter out image files
        # filtered_iterator = page_iterator.search("Contents[?contains('Key','json') == `False`]")
        # filtered_iterator = page_iterator.search("Contents.Key[?contains(@,'json') == `False`][]")
        # filtered_iterator = page_iterator.search("[?contains(Contents.Key,'json') == `false`][]")
        # page_iterator:
        for page in page_iterator:
            image_list.extend([dat["Key"].replace(full_image_group_path, "") for dat in page["Contents"] if
                               '.json' not in dat["Key"]])

        return image_list


class getVolumeInfosBUDA(GetVolumeInfoBase):
    """
    this uses the LDS-PDI capabilities to get the volume list of a work, including, for each volume:
    - image list
    - image group ID

    The information should be fetched (in csv or json) from lds-pdi, query for W22084 for instance is:
    http://purl.bdrc.io/query/Work_ImgList?R_RES=bdr:W22084&format=csv&profile=simple&pageSize=500
    """

    def fetch(self, workRid: str) -> []:
        """
        BUDA LDS-PDU implementation
        :return: VolInfo[]
        """
        vol_info = []
        req = f'http://purl.bdrc.io/query/table/Work_ImgList?R_RES=bdr:{workRid}&format=csv&profile=simple&pageSize=500'
        with request.urlopen(req) as response:
            info = response.read()
            info = info.decode('utf8').strip()
            for line in info.split('\n')[1:]:
                _, l, g = line.replace('"', '').split(',')
                vi = VolInfo(l, g)
                vol_info.append(vi)

        return vol_info


class getVolumeInfoseXist(GetVolumeInfoBase):
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

        # Interesting first pass failure: @ urllib.error.URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]
        # certificate verify failed (_ssl.c:777)> Tried fix
        req = f'http://www.tbrc.org/public?module=work&query=work-igs&args={work_rid}'

        vol_info = []
        from lxml import etree
        try:

            with request.urlopen(req) as response:
                info = response.read()
                info = info.decode('utf8').strip()

                # work-igs returns one node with space delimited list of image groups
                igs: str = etree.fromstring(info).text.split(" ")
                vol_info = self.expand_groups(work_rid, igs)
        except:
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
            vol_infos = self.get_image_names(work_rid, ig)
            vi.append(VolInfo(vol_infos, ig))

        return vi



    def getImageNames(self, workRid: str, imageGroup: str) -> str:
        """
        Emulates BUDA fetch, of a volInfo, with a first image filename ; count
        :param workRid:
        :param imageGroup:
        :return: VolInfo[] with one tuple for each image group
        """
        images = []
        full_image_group_path: str = getS3FolderPrefix.getS3FolderPrefix(workRid,imageGroup)
        page_iterator = self.botoPaginator.paginate(Bucket=f"archive.tbrc.org",
                                                       Prefix=full_image_group_path)

        baseImageName = ""
        nFiles = 0
        for page in page_iterator:

            #strip out the prefix
            # Emulate the BUDA interface which just sends the first file path and the count (see GetVolumeInfosBUDA)
            # Note that tbrc has to deal with an impure file system which may not have only image files
            # in it.
            fs = [dat["Key"].replace(full_image_group_path, "") for dat in page["Contents"]]
            #
            # Filter out files without image group name in them
            fs = [ x for x in fs if imageGroup in x]
            if not baseImageName:
                baseImageName = page['Contents'][0]["Key"].replace(full_image_group_path,"")

            nFiles += len(fs)  # page["Contents"])
            # If I wanted the actual data, I'd do this
            # fs = [dat["Key"].replace(full_image_group_path,"") for dat in page["Contents"]]
            # images.extend(fs)

        # This is BUDA's return for the query
        base_file =  f'{baseImageName}:{nFiles}'
        return base_file
