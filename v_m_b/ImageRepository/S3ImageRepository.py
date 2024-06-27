import hashlib
import io
import sys
from typing import Tuple

import boto3
import botocore
from boto.s3.bucket import Bucket
from s3pathlib import S3Path

# from manifestCommons import *
import v_m_b.manifestCommons as Common
from v_m_b.ImageRepository.ImageRepositoryBase import ImageRepositoryBase
from v_m_b.image.generateManifest import fillDataWithBlobImage
from v_m_b.s3customtransfer import S3CustomTransfer


class S3ImageRepository(ImageRepositoryBase):

    def upload_manifest(self, *args):
        pass


    def __init__(self, client: boto3.client, dest_bucket: Bucket, images_name: str):
        """
        Initialize
        :param bom:name of Bill of Materials
        """
        super(S3ImageRepository, self).__init__(images_name)
        self._client = client
        self._bucket = dest_bucket
        self._boto_paginator = self._client.get_paginator('list_objects_v2')


    def fillData(self, transfer, s3imageKey, imgdata):
        """
        Launch async transfer with callback
        """
        buffer = io.BytesIO()
        try:
            transfer.download_file(self._bucket.name, s3imageKey, buffer,
                                   callback=DoneCallback(buffer, imgdata))
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                self.repo_log.error(f"S3 object {s3imageKey} not found.")
            else:
                ee = sys.exc_info()
                self.repo_log.error(f"S3 Exception ei[0]:{ee[0]} ei[1]:{ee[1]}")
                raise
        finally:
            # self.repo_log.debug(imgdata)
            pass

    def generateManifest(self, work_Rid: str, vol_info: str) -> []:
        res = []
        transfer = S3CustomTransfer(self._client)
        parent: S3Path = self.resolve_image_group(work_Rid, vol_info)
        #
        self.repo_log.debug(vol_info)
        for image_s3 in parent.iter_objects():
            if image_s3.is_file():
                image_file_name: str = image_s3.fname
                image_key:str = image_s3.key
                imgdata = {"filename": image_file_name}
                res.append(imgdata)
                self.fillData(transfer, image_key, imgdata)

        transfer.wait()
        return self.clean_manifest(res)


    def uploadManifest(self, work_rid: str, image_group: str, bom_name: str, manifest_zip: bytes):
        """
         - upload on s3 with the right metadata:
          - ContentType='application/json'
          - ContentEncoding='gzip'
          - key: s3folderPrefix+"dimensions.json" (making sure there is a /)
        :param work_rid:
        :param image_group:
        :param bom_name:
        :param manifest_zip:
        :return:
        """
        key: S3Path = S3Path(self.resolve_image_group(work_rid, image_group), bom_name)
        self.repo_log.debug("writing " + key.fname)
        from botocore.exceptions import ClientError
        try:
            self._client.put_object(Key=key.key, Body=manifest_zip,
                                    Metadata={'ContentType': 'application/json', 'ContentEncoding': 'gzip'},
                                    Bucket=self._bucket.name)
            self.repo_log.info("wrote " + key.fname)
        except ClientError:
            self.repo_log.warn(f"Couldn't write json {key.abspath}")

    def resolve_image_group(self, work_rid: str, image_group_disk: str) -> S3Path:
        """
        Fully qualifies a RID and a Path
        :param work_rid:
        :param image_group_disk: Image group folder name
        :return: fully qualified path to image group on disk.
        """
        from archive_ops.api import get_s3_location
        from pathlib import PurePath

        # '/' is the separator per the AWS S3 object naming spec
        locator: str = '/'.join(
            PurePath(get_s3_location(Common.VMT_WORK_PARENT, work_rid)).parts
            + PurePath( self.images_folder_name, f"{work_rid}-{image_group_disk}").parts)

        return S3Path(self._bucket.name, locator)



class DoneCallback(object):
    def __init__(self, buffer, imgdata):
        self._buffer = buffer
        self._imgdata = imgdata

    def __call__(self):
        fillDataWithBlobImage(self._buffer, self._imgdata)
