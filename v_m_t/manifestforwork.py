#!/usr/bin/env python3
import argparse
import csv
import gzip
import io
import json
import logging
import os
from tempfile import NamedTemporaryFile
from threading import Lock
from typing import TextIO

import boto3
import botocore
from PIL import Image
from boto.s3.bucket import Bucket

from .AOLogger import AOLogger
from .S3WorkFileManager import S3WorkFileManager
from .getS3FolderPrefix import get_s3_folder_prefix
from .s3customtransfer import S3CustomTransfer

S3_DEST_BUCKET: str = "archive.tbrc.org"

# for manifestFromS3
S3_MANIFEST_WORK_LIST_BUCKET: str = "manifest.bdrc.org"
LOG_FILE_ROOT: str = "/var/log/VolumeManifestTool"
todo_prefix: str = "processing/todo/"
processing_prefix: str = "processing/inprocess/"
done_prefix: str = "processing/done/"

# jimk Toggle legacy and new sources
BUDA_IMAGE_GROUP = True

csvlock: Lock = Lock()

s3_work_manager: S3WorkFileManager = S3WorkFileManager(S3_MANIFEST_WORK_LIST_BUCKET, todo_prefix, processing_prefix,
                                                       done_prefix)

shell_logger: AOLogger = None


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

    args = prolog()

    session = boto3.session.Session(region_name='us-east-1')
    client = session.client('s3')
    import time

    while True:
        try:
            work_list = buildWorkListFromS3(client)

            for s3Path in work_list:
                s3_full_path = f'{processing_prefix}{s3Path}'

                # jimk: need to pass a file-like object. NamedTemporaryFile returns an odd
                # beast which you cant run readlines() on
                file_path = NamedTemporaryFile()
                client.download_file(S3_MANIFEST_WORK_LIST_BUCKET, s3_full_path, file_path.name)

                with open(file_path.name, 'r') as srcFile:
                    manifestForList(srcFile)

            # don't need to rename work_list. Only when moving from src to done
            if len(work_list) > 0:
                s3_work_manager.mark_done(work_list, work_list)
        except Exception as eek:
            shell_logger.log(logging.ERROR, eek)
        time.sleep(abs(args.poll_interval))


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

    _parser = argparse.ArgumentParser(description="Prepares an inventory of image dimensions",
                                      usage="%(prog)s sourcefile.")

    _parser.add_argument("-d", "--debugLevel", dest='log_level', action='store',
                         choices=['info', 'warning', 'error', 'debug', 'critical'], default='info',
                         help="choice values are from python logging module")

    _parser.add_argument("-l", "--logDir", dest='log_parent', action='store', default='/tmp',
                         help="Path to log file directory")

    _parser.add_argument("-c", '--checkImageInternals', dest='check_image_internals', action='store', type=bool,
                         default=False, help="Check image internals (slower)")
    #
    # sourceFile only used in manifestForList
    _parser.add_argument('sourceFile', help="File containing one RID per line.", nargs='?', type=argparse.FileType('r'))
    _parser.add_argument('-i', '--interval', dest='poll_interval', help="Seconds between alerts for file.",
                         required=False, default=60, type=int)
    # noinspection PyTypeChecker
    _parser.parse_args(namespace=arg_namespace)


def exception_handler(exception_type, exception, traceback):
    """
    All your trace are belong to us!
    your format
    """
    error_string: str = f"{exception_type.__name__}: {exception}"

    if shell_logger is None:
        print(error_string)
    else:
        shell_logger.exception(error_string)


def prolog(log_level_root="/tmp/VolumeManifestTool") -> object:
    # Skip noisy exceptions
    import sys
    from pathlib import Path
    global shell_logger
    # sys.tracebacklimit = 0
    sys.excepthook = exception_handler

    args = GetArgs()
    parse_args(args)
    shell_logger = AOLogger(__name__, args.log_level, Path(args.log_parent))

    return args


# region
def manifestForList(sourceFile: TextIO):
    """
    reads a file containing a list of work RIDs and iterate the manifestForWork function on each.
    The file can be of a format the developer like, it doesn't matter much (.txt, .csv or .json)
    """
    global shell_logger

    if sourceFile is None:
        raise ValueError("Usage: manifestforwork sourceFile where sourceFile contains a list of work RIDs")

    session = boto3.session.Session(region_name='us-east-1')
    client = session.client('s3')
    dest_bucket = session.resource('s3').Bucket(S3_DEST_BUCKET)
    errors_file_name = "errors-" + os.path.basename(sourceFile.name) + ".csv"
    with open(errors_file_name, 'w+', newline='') as csvf:
        csvwriter = csv.writer(csvf, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        csvwriter.writerow(
            ["s3imageKey", "workRID", "imageGroupID", "size", "width", "height", "mode", "format", "palette",
             "compression", "errors"])
        with sourceFile as f:
            for work_rid in f.readlines():
                work_rid = work_rid.strip()
                try:
                    manifestForWork(client, dest_bucket, work_rid, csvwriter)
                except Exception as inst:

                    shell_logger.error(f"{work_rid} failed to build manifest {type(inst)} {inst.args} {inst} ")



def manifestForWork(client: boto3.client, bucket: Bucket, workRID, csvwriter):
    """
    this function generates the manifests for each volume of a work RID (example W22084)
    """

    global shell_logger

    vol_infos: [] = getVolumeInfos(workRID, client, bucket)
    if len(vol_infos) == 0:
        shell_logger.error(f"Could not find image groups for {workRID}")
        return

    for vi in vol_infos:
        manifestForVolume(client, workRID, vi, csvwriter)



def manifestForVolume(client, workRID, vi, csvwriter):
    """
    this function generates the manifest for an image group of a work (example: I0886 in W22084)
    """

    global shell_logger

    s3_folder_prefix: str = get_s3_folder_prefix(workRID, vi.imageGroupID)
    if manifestExists(client, s3_folder_prefix):
        shell_logger.info("manifest exists: " + workRID + "-" + vi.imageGroupID)  # return
    manifest = generateManifest(client, s3_folder_prefix, vi.imageList, csvwriter, workRID, vi.imageGroupID)
    uploadManifest(client, s3_folder_prefix, manifest)


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


def generateManifest(client, s3folderPrefix, imageList, csvwriter, workRID, imageGroupID):
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


def fillDataWithBlobImage(blob, data, csvwriter, s3imageKey, workRID, imageGroupID):
    """
    This function returns a dict containing the height and width of the image
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
    :param bucket: storage parent
    :type bucket: boto.Bucket
    :return: VolList[imagegroup1..imagegroupn]
    """
    from .VolumeInfoBuda import VolumeInfoBUDA
    from .VolumeInfoeXist import VolumeInfoeXist

    vol_infos: [] = []
    if BUDA_IMAGE_GROUP:
        vol_infos = (VolumeInfoBUDA(botoClient, bucket)).fetch(workRid)

    if len(vol_infos) == 0:
        vol_infos = (VolumeInfoeXist(botoClient, bucket)).fetch(workRid)

    return vol_infos


def buildWorkListFromS3(client: object) -> (str, []):
    """
    Reads a well-known folder for files which contain works.
    Downloads, and digests each file, moving it to a temporary processing folder.
    :param client: S3 client
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

    # mon
    if len(file_list) == 0:
        shell_logger.debug("no name")
    else:
        shell_logger.info(f"found names {file_list}")

    return new_names


if __name__ == '__main__':
    main()  #  #   manifestFromS3()
