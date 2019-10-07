import abc
import collections

from boto3 import client
from botocore.paginate import Paginator

from .getS3FolderPrefix import get_s3_folder_prefix

# imageList is a str[], imageGroupId: str
VolInfo = collections.namedtuple('VolInfo', ['imageList', 'imageGroupID'])


class VolumeInfoBase(metaclass=abc.ABCMeta):
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

    def get_image_names_from_S3(self, parent, str, work_rid: str, image_group: str) -> []:
        """
        get names of the image files (actually, all the files in an image group, regardless
        :type image_group: str
        :param work_rid: work name ex: W1FPl2251
        :param image_group: sub folder (e.g. I1CZ0085)
        :return: str[]  should contain I1CZ0085
        """

        image_list = []
        full_image_group_path: str = get_s3_folder_prefix(work_rid, image_group)
        page_iterator = self.boto_paginator.paginate(Bucket=parent, Prefix=full_image_group_path)

        # #10 filter out image files
        # filtered_iterator = page_iterator.search("Contents[?contains('Key','json') == `False`]")
        # filtered_iterator = page_iterator.search("Contents.Key[?contains(@,'json') == `False`][]")
        # filtered_iterator = page_iterator.search("[?contains(Contents.Key,'json') == `false`][]")
        # page_iterator:
        for page in page_iterator:
            if "Contents" in page:
                image_list.extend([dat["Key"].replace(full_image_group_path, "") for dat in page["Contents"] if
                                   '.json' not in dat["Key"]])

        return image_list
