import io

import boto3
import botocore
from boto.s3.bucket import Bucket

# from manifestCommons import *
import manifestCommons as Common
from VolumeInfo.VolInfo import VolInfo
from getS3FolderPrefix import get_s3_folder_prefix
from s3customtransfer import S3CustomTransfer
from .ImageRepositoryBase import ImageRepositoryBase


class S3ImageRepository(ImageRepositoryBase):

    def upload_manifest(self, *args):
        pass

    def get_bom(self):
        """

        :return: text of volume bill of materials
        """
        pass

    def __init__(self, bom: str, client: boto3.client, dest_bucket: Bucket):
        """
        Initialize
        :param bom:name of Bill of Materials
        """
        super(S3ImageRepository, self).__init__(bom)
        self._client = client
        self._bucket = dest_bucket

    def manifest_exists(self, work_Rid: str, image_group_id: str):
        """
        make sure s3folderPrefix+"/dimensions.json" doesn't exist in S3
        """
        key = get_s3_folder_prefix(work_Rid, image_group_id) + 'dimensions.json'
        try:
            self._client.head_object(Bucket=Common.S3_DEST_BUCKET, Key=key)
            return True
        except botocore.exceptions.ClientError as exc:
            if exc.response['Error']['Code'] == '404':
                return False
            else:
                raise

    def fillData(self, transfer, s3imageKey, imgdata):
        """
        Launch async transfer with callback
        """
        buffer = io.BytesIO()
        try:
            transfer.download_file(Common.S3_DEST_BUCKET, s3imageKey, buffer,
                                   callback=DoneCallback(buffer, imgdata))
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                self.repo_log.error(f"S3 object {s3imageKey} not found.")
            else:
                raise

    def generateManifest(self, work_Rid: str, vol_info: VolInfo) -> []:
        res = []
        transfer = S3CustomTransfer(self._client)
        parent: str = get_s3_folder_prefix(work_Rid, vol_info.imageGroupID)
        #
        # jkmod: moved expand_image_list into VolumeInfoBUDA class
        for imageFileName in vol_info.image_list:
            image_key: str = parent + imageFileName
            imgdata = {"filename": imageFileName}
            res.append(imgdata)
            self.fillData(transfer, image_key, imgdata)

        transfer.wait()
        return res

    def getImageNames(self, work_Rid: str, image_group: str, bom_name: str) -> []:
        """
        S3 implementation of get Image Names

        """

        image_list = []

        full_image_group_path: str = get_s3_folder_prefix(work_Rid, image_group)
        bom_path: str = full_image_group_path + bom_name
        # noinspection PyBroadException
        try:
            bom: [] = self.read_bom_from_s3(bom_path)

            if len(bom) > 0:
                self.repo_log.debug(
                    f"fetched BOM from BUDA BOM: {len(bom)} entries path:{bom_path}:")
                return bom

            # no BOM. Enumerate the files
            page_iterator = self._client.boto_paginator.paginate(Bucket=self._bucket.name, Prefix=full_image_group_path)

            # #10 filter out image files
            # filtered_iterator = page_iterator.search("Contents[?contains('Key','json') == `False`]")
            # filtered_iterator = page_iterator.search("Contents.Key[?contains(@,'json') == `False`][]")
            # filtered_iterator = page_iterator.search("[?contains(Contents.Key,'json') == `false`][]")

            # Strip out the path components of all non json files in the prefix
            for page in page_iterator:
                if "Contents" in page:
                    image_list.extend([dat["Key"].replace(full_image_group_path, "") for dat in page["Contents"] if
                                       '.json' not in dat["Key"]])

            self.repo_log.debug(
                f"fetched BOM from S3 list_objects: {len(image_list)} entries. path:{full_image_group_path}")
        except Exception:
            self.repo_log.warning(f"Could not populate BOM for {bom_path}")
        finally:
            pass
        return image_list

    def read_bom_from_s3(self, bom_path: str) -> list:
        """
        Reads a json file and returns the values with the "filename" key as a list of strings
        :param bom_path:  full s3 path to BOM
        :return:
        """
        import boto3
        import json

        s3 = boto3.client('s3')
        json_body: {} = {}

        from botocore.exceptions import ClientError
        try:
            obj = s3.get_object(Bucket=self._bucket.name, Key=bom_path)
            #
            # Python 3 read() returns bytes which need decode
            json_body = json.loads(obj['Body'].read().decode('utf - 8'))

            self.repo_log.info("read bom from s3 object size %d json body size %d path %s",
                               len(obj), len(json_body), bom_path)
        except ClientError as ex:
            errstr: str = f"ClientError Exception {ex.response['Error']['Code']} Message " \
                    " f{ex.response['Error']['Message']} on object {ex.response['Error']['Key']} " \
                          "for our BOMPath  {bom_path}  from bucket {self._bucket.name}"

            if ex.response['Error']['Code'] == 'NoSuchKey':
                self.repo_log.warning(errstr)
            else:
                self.repo_log.error(errstr)
                raise

        return [x[Common.VMT_BUDABOM_JSON_KEY] for x in json_body]

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



class DoneCallback(object):
    def __init__(self, buffer, imgdata):
        self._buffer = buffer
        self._imgdata = imgdata

    def __call__(self):
        Common.fillDataWithBlobImage(self._buffer, self._imgdata)
