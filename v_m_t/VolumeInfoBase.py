import abc
import collections
import logging

from boto.s3.bucket import Bucket
from boto3 import client
from botocore.paginate import Paginator

from .getS3FolderPrefix import get_s3_folder_prefix

# imageList is a str[], imageGroupId: str
VolInfo = collections.namedtuple('VolInfo', ['imageList', 'imageGroupID'])

#
# Super magic constant.
# See https://github.com/archive-ops/scripts/processing/sync2archive.sh
#
VMT_BUDABOM: str = 'fileList.json'
VMT_BUDABOM_KEY = 'filename'
VMT_DIM: str = 'dimensions.json'

logger: logging = None


class VolumeInfoBase(metaclass=abc.ABCMeta):
    """
    Gets volume info for a work.
    Passes request off to subclasses
    """

    boto_client: client = None

    s3_image_bucket: Bucket = None

    # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/paginators.html
    boto_paginator: Paginator = None

    def __init__(self, boto_client: client, bucket: Bucket):
        """
        :param boto_client: context for operations
        :type boto_client: boto3.client
        : param bucket: target container
        :type bucket: boto.s3.bucket.Bucket
        """
        self.boto_client = boto_client
        self.boto_paginator = self.boto_client.get_paginator('list_objects_v2')
        self.s3_image_bucket = bucket
        self.logger = logging.getLogger(__name__)

    @abc.abstractmethod
    def fetch(self, urlRequest) -> []:
        """
        Subclasses implement
        :param urlRequest:
        :return: VolInfo[] with  one entry for each image in the image group
        """
        pass

    def read_bom_from_s3(self, bom_path: str) -> list:
        """
        Reads a json file and returns the values with the "filename" key as a list of strings
        :param bom_path:  full s3 path to BOM
        :return:
        """
        import boto3
        import json

        s3 = boto3.client('s3')

        obj = s3.get_object(Bucket=self.s3_image_bucket.name, Key=bom_path)
        #
        # Python 3 read() returns bytes which need decode
        json_body: {} = json.loads(obj['Body'].read().decode('utf - 8'))

        self.logger.debug("read bom from s3 object size %d json body size %d", len(obj), len(json_body))

        return [x[VMT_BUDABOM_KEY] for x in json_body]

    def get_image_names_from_S3(self, work_rid: str, image_group: str) -> []:
        """
        get names of the image files (actually, all the files in an image group, regardless
        :param work_rid: work name ex: W1FPl2251
        :param image_group: sub folder (e.g. I1CZ0085)
        :return: str[]  should contain ['I1CZ0085001.jpg','I1CZ0085002.jpg'...']
        """

        image_list = []
        full_image_group_path: str
        try:
            full_image_group_path = get_s3_folder_prefix(work_rid, image_group)
            bom: [] = self.read_bom_from_s3(full_image_group_path + VMT_BUDABOM)

            if len(bom) > 0:
                self.logger.debug(f"fetched BOM from BUDA BOM: {len(bom)} entries")
                return bom

            # jimk: Get the
            page_iterator = self.boto_paginator.paginate(Bucket=self.s3_image_bucket.name, Prefix=full_image_group_path)

            # #10 filter out image files
            # filtered_iterator = page_iterator.search("Contents[?contains('Key','json') == `False`]")
            # filtered_iterator = page_iterator.search("Contents.Key[?contains(@,'json') == `False`][]")
            # filtered_iterator = page_iterator.search("[?contains(Contents.Key,'json') == `false`][]")
            # page_iterator:
            for page in page_iterator:
                if "Contents" in page:
                    image_list.extend([dat["Key"].replace(full_image_group_path, "") for dat in page["Contents"] if
                                       '.json' not in dat["Key"]])

            self.logger.debug(f"fetched BOM from S3 list_objects: {len(image_list)} entries.")
        except Exception as eek:
            self.logger.warning(f"Could not populate BOM from S3 {full_image_group_path}")
        finally:
            pass
        return image_list
