import io
from abc import ABC

import boto3
import botocore
from boto.s3.bucket import Bucket

from .ImageRepositoryBase import ImageRepositoryBase

class S3ImageRepository(ImageRepositoryBase):

    def manifest_exists(self, *args) -> bool:
        pass

    def upload_manifest(self, *args):
        pass

    def generate_manifest(self, *args):
        pass

    def get_bom(self):
        """

        :return: text of volume bill of materials
        """
        pass

    def __init__(self, bom: object, client: boto3.client, dest_bucket: Bucket) -> object:
        """
        Initialize
        :param bom:name of Bill of Materials
        """
        super(S3ImageRepository, self).__init__(bom)
        self._client = client
        self._bucket = dest_bucket



def manifestExists(client, s3folderPrefix):
    """
    make sure s3folderPrefix+"/dimensions.json" doesn't exist in S3
    """
    key = s3folderPrefix + 'dimensions.json'
    try:
        client.head_object(Bucket=S3_DEST_BUCKET, Key=key)
        return True
    except botocore.exceptions.ClientError as exc:
        if exc.response['Error']['Code'] == '404':
            return False
        else:
            raise


def gets3blob(bucket, s3imageKey):
    f = io.BytesIO()
    try:
        bucket.download_fileobj(s3imageKey, f)
        return f
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            return None
        else:
            raise


class DoneCallback(object):
    def __init__(self, filename, imgdata, csvwriter, s3imageKey, workRID, imageGroupID):
        self._filename = filename
        self._imgdata = imgdata
        self._csvwriter = csvwriter
        self._s3imageKey = s3imageKey
        self._workRID = workRID
        self._imageGroupID = imageGroupID

    def __call__(self):
        fillDataWithBlobImage(self._filename, self._imgdata, self._csvwriter, self._s3imageKey, self._workRID,
                              self._imageGroupID)


def fillData(transfer, s3imageKey, csvwriter, imgdata, workRID, imageGroupID):
    """
    Launch async transfer with callback

    """
    filename = io.BytesIO()
    try:
        transfer.download_file(S3_DEST_BUCKET, s3imageKey, filename,
                               callback=DoneCallback(filename, imgdata, csvwriter, s3imageKey, workRID, imageGroupID))
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            csvline = [s3imageKey, workRID, imageGroupID, "", "", "", "", "", "", "", "keydoesnotexist"]
            report_error(csvwriter, csvline)
        else:
            raise


def generate_manifest(client, s3folderPrefix, imageList, csvwriter, workRID, imageGroupID):
    """
    this actually generates the manifest. See example in the repo. The example corresponds to W22084, image group I0886.
    :param client:
    :param s3folderPrefix:
    :param imageList: list of image names
    :param csvwriter:
    :param workRID:
    :param imageGroupID:
    :return:
    """
    res = []
    transfer = S3CustomTransfer(client)
    #
    # jkmod: moved expand_image_list into VolumeInfoBUDA class
    for imageFileName in imageList:
        s3imageKey: str = s3folderPrefix + imageFileName
        imgdata = {"filename": imageFileName}
        res.append(imgdata)
        fillData(transfer, s3imageKey, csvwriter, imgdata, workRID, imageGroupID)

    transfer.wait()
    return res
