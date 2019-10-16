#!/usr/bin/env python3
import argparse
import csv
import gzip
import io
import json
import os
from tempfile import NamedTemporaryFile
from threading import Lock

import boto3
import botocore
import logging
from PIL import Image
from boto.s3.bucket import Bucket

from .S3WorkFileManager import S3WorkFileManager
from .getS3FolderPrefix import get_s3_folder_prefix
from .s3customtransfer import S3CustomTransfer
from .init_app_logger import init_app_logger

S3_DEST_BUCKET: str = "archive.tbrc.org"

S3_MANIFEST_WORK_LIST_BUCKET: str = "manifest.bdrc.org"
todo_prefix: str = "processing/todo/"
processing_prefix: str = "processing/inprocess/"
done_prefix: str = "processing/done/"

# jimk Toggle legacy and new sources
BUDA_IMAGE_GROUP = True

csvlock: Lock = Lock()

s3_work_manager: S3WorkFileManager = S3WorkFileManager(S3_MANIFEST_WORK_LIST_BUCKET, todo_prefix, processing_prefix,
                                                       done_prefix)

shell_logger: logging = None


# os.environ['AWS_SHARED_CREDENTIALS_FILE'] = "/etc/buda/volumetool/credentials"

def report_error(csvwriter, csvline):
    """
   write the error in a synchronous way
   """
    global csvlock
    csvlock.acquire()
    csvwriter.writerow(csvline)
    csvlock.release()


# region shells
#  These are the entry points. See setup.py, which configures 'manifestfromS3' and 'manifestforwork:main' as console
# entry points
def main():
    """
    reads the first argument of the command line and pass it as filename to the manifestForList function
    """
    # manifestForList('RIDs.txt') # uncomment to test locally
    manifestShell()


# noinspection PyPep8Naming
def manifestFromS3():
    """
    Retrieves processes S3 objects in a bucket/key pair, where key is a prefix
    :return:
    """

    prolog()

    session = boto3.session.Session(region_name='us-east-1')
    client = session.client('s3')
    import time

    while True:
        try:
            work_list = buildWorkListFromS3(session, client)

            for s3Path in work_list:
                s3_full_path = f'{processing_prefix}{s3Path}'
                file_path = NamedTemporaryFile()
                client.download_file(S3_MANIFEST_WORK_LIST_BUCKET, s3_full_path, file_path.name)
                manifestForList(file_path.name)

            # don't need to rename work_list. Only when moving from src to done
            if len(work_list) > 0:
                s3_work_manager.mark_done(work_list, work_list)
        except Exception as eek:
            shell_logger.exception(eek)
        time.sleep(6)


def manifestShell():
    """
    Prepares args for running
    :return:
    """
    args = prolog()

    manifestForList(args.sourceFile)


# region Argparse
class GetArgs:
    """
    instantiates command line argument container
    """
    pass


def parse_args(arg_namespace: object) -> None:
    """
    :rtype: object
    :param arg_namespace. class which holds arg values
    """
    from v_m_t.init_app_logger import existing_log_level

    _parser = argparse.ArgumentParser(description="Prepares an inventory of image dimensions",
                                      usage="%(prog)s sourcefile.")
    _parser.add_argument("-l", "--loglevel", dest='log_level', action='store', type=existing_log_level, default='info')
    #
    # sourceFile only used in manifestForList
    _parser.add_argument('-s', '--sourceFile', dest='sourceFile', help="File containing one RID per line.",
                         required=False)

    # noinspection PyTypeChecker
    _parser.parse_args(namespace=arg_namespace)


def prolog() -> object:
    args = GetArgs()
    parse_args(args)
    init_app_logger(args.log_level)
    global shell_logger
    shell_logger = logging.getLogger(__name__)
    return args


# region

def manifestForList(filename):
    """
    reads a file containing a list of work RIDs and iterate the manifestForWork function on each.
    The file can be of a format the developer like, it doesn't matter much (.txt, .csv or .json)
    """
    session = boto3.session.Session(region_name='us-east-1')
    client = session.client('s3')
    dest_bucket = session.resource('s3').Bucket(S3_DEST_BUCKET)
    errors_file_name = "errors-" + os.path.basename(filename) + ".csv"
    with open(errors_file_name, 'w+', newline='') as csvf:
        csvwriter = csv.writer(csvf, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        csvwriter.writerow(
            ["s3imageKey", "workRID", "imageGroupID", "size", "width", "height", "mode", "format", "palette",
             "compression", "errors"])
        with open(filename, 'r') as f:
            for workRID in f.readlines():
                workRID = workRID.strip()
                manifestForWork(client, dest_bucket, workRID, csvwriter)


def manifestForWork(client: boto3.client, bucket : Bucket, workRID, csvwriter):
    """
    this function generates the manifests for each volume of a work RID (example W22084)
    """

    global shell_logger
    vol_infos: [] = getVolumeInfos(workRID, client, bucket)
    if (len(vol_infos) == 0):
        shell_logger.error(f"Could not find image groups for {workRID}")
        return

    for vi in vol_infos:
        manifestForVolume(client, bucket, workRID, vi, csvwriter)


def manifestForVolume(client, bucket, workRID, vi, csvwriter):
    """
    this function generates the manifest for an image group of a work (example: I0886 in W22084)
    """

    global shell_logger

    s3folderPrefix = get_s3_folder_prefix(workRID, vi.imageGroupID)
    if manifestExists(client, s3folderPrefix):
        shell_logger.info("manifest exists: " + workRID + "-" + vi.imageGroupID)  # return
    manifest = generateManifest(bucket, client, s3folderPrefix, vi.imageList, csvwriter, workRID, vi.imageGroupID)
    uploadManifest(client, s3folderPrefix, manifest)


def gzip_str(string_):
    # taken from https://gist.github.com/Garrett-R/dc6f08fc1eab63f94d2cbb89cb61c33d
    out = io.BytesIO()

    with gzip.GzipFile(fileobj=out, mode='w') as fo:
        fo.write(string_.encode())

    bytes_obj = out.getvalue()
    return bytes_obj


def uploadManifest(bucket, s3folderPrefix, manifestObject):
    """
    inspire from:
    https://github.com/buda-base/drs-deposit/blob/2f2d9f7b58977502ae5e90c08e77e7deee4c470b/contrib/tojsondimensions.py#L68

    in short:
       - make a compressed json string (no space)
       - gzip it
       - upload on s3 with the right metadata:
          - ContentType='application/json'
          - ContentEncoding='gzip'
          - key: s3folderPrefix+"dimensions.json" (making sure there is a /)
    """

    global shell_logger

    manifest_str = json.dumps(manifestObject)
    manifest_gzip = gzip_str(manifest_str)

    key = s3folderPrefix + 'dimensions.json'
    shell_logger.info("writing " + key)
    bucket.put_object(Key=key, Body=manifest_gzip,
                      Metadata={'ContentType': 'application/json', 'ContentEncoding': 'gzip'}, Bucket=S3_DEST_BUCKET)


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


def fillData(bucket, client, transfer, s3imageKey, csvwriter, imgdata, workRID, imageGroupID):
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


def generateManifest(bucket, client, s3folderPrefix, imageList, csvwriter, workRID, imageGroupID):
    """
    this actually generates the manifest. See example in the repo. The example corresponds to W22084, image group I0886.
    :param bucket:
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
        s3imageKey = s3folderPrefix + imageFileName
        imgdata = {"filename": imageFileName}
        res.append(imgdata)
        fillData(bucket, client, transfer, s3imageKey, csvwriter, imgdata, workRID, imageGroupID)

    transfer.wait()
    return res


def fillDataWithBlobImage(blob, data, csvwriter, s3imageKey, workRID, imageGroupID):
    """
    This function returns a dict containing the heigth and width of the image
    the image is the binary blob returned by s3, an image library should be used to treat it
    please do not use the file system (saving as a file and then having the library read it)

    This could be coded in a faster way, but the faster way doesn't work with group4 tiff:
    https://github.com/python-pillow/Pillow/issues/3756

    For pilmode, see
    https://pillow.readthedocs.io/en/5.1.x/handbook/concepts.html#concept-modes

    They are different from the Java ones:
    https://docs.oracle.com/javase/8/docs/api/java/awt/image/BufferedImage.html

    but they should be enough. Note that there's no 16 bit
    """
    errors = []
    size = blob.getbuffer().nbytes
    im = Image.open(blob)
    data["width"] = im.width
    data["height"] = im.height
    # we indicate sizes of the more than 1MB
    if size > 1000000:
        data["size"] = size
    if size > 400000:
        errors.append("toolarge")
    compression = ""
    final4 = s3imageKey[-4:].lower()
    if im.format == "TIFF":
        compression = im.info["compression"]
        if im.info["compression"] != "group4":
            errors.append("tiffnotgroup4")
        if im.mode != "1":
            errors.append("nonbinarytif")
            data["pilmode"] = im.mode
        if final4 != ".tif" and final4 != "tiff":
            errors.append("extformatmismatch")
    elif im.format == "JPEG":
        if final4 != ".jpg" and final4 != "jpeg":
            errors.append("extformatmismatch")
    else:
        errors.append("invalidformat")
    # in case of an uncompressed raw, im.info.compression == "raw"
    if errors:
        csvline = [s3imageKey, workRID, imageGroupID, size, im.width, im.height, im.mode, im.format, im.palette,
                   compression, "-".join(errors)]
        report_error(csvwriter, csvline)


def getVolumeInfos(workRid: str, botoClient: object, bucket: Bucket) -> []:
    """
    Tries data sources for image group info. If BUDA_IMAGE_GROUP global is set, prefers
    BUDA source, tries eXist on BUDA fail.
    :type workRid: str
    :param workRid: Work identifier
    :param botoClient: handle to AWS
    :return: VolList[imagegroup1..imagegroupn]
    """
    from .VolumeInfoBuda import VolumeInfoBUDA
    from .VolumeInfoeXist import VolumeInfoeXist

    vol_infos: [] = []
    if BUDA_IMAGE_GROUP:
        vol_infos = (VolumeInfoBUDA(botoClient, bucket)).fetch(workRid)

    if (len(vol_infos) == 0):
        vol_infos = (VolumeInfoeXist(botoClient, bucket)).fetch(workRid)

    return vol_infos


def buildWorkListFromS3(session: object, client: object) -> (str, []):
    """
    Reads a well-known folder for files which contain works.
    Downloads, and digests each file, moving it to a temporary processing folder.
    :param session: S3 session
    :param client: S3 client
    :type session: boto3.session
    :type client: boto3.client
    :return: unnamed tuple  of source directory and file names which have to be processed.
    """
    global shell_logger

    page_iterator = client.get_paginator('list_objects_v2').paginate(Bucket=S3_MANIFEST_WORK_LIST_BUCKET,
                                                                     Prefix=todo_prefix)

    file_list = []
    # Get the object list from the first value
    for page in page_iterator:
        object_list = [x for x in page["Contents"]]
        file_list.extend([x['Key'].replace(todo_prefix, '') for x in object_list if x['Key'] != todo_prefix])

    # We've ingested the contents of the to do list, move the files into processing
    new_names = [s3_work_manager.local_name_work_file(x) for x in file_list]

    s3_work_manager.mark_underway(file_list, new_names)
    shell_logger.info(f"found names {file_list}")

    return new_names


if __name__ == '__main__':
    # main()
    manifestFromS3()
