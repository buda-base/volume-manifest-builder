#!/usr/bin/env python3
import argparse
import gzip
import io
import json
import logging
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock
from typing import TextIO

import boto3
import botocore
from PIL import Image
from boto.s3.bucket import Bucket
from botocore.exceptions import ClientError

from AOLogger import AOLogger
from ImageGroupResolver import ImageGroupResolver
from S3WorkFileManager import S3WorkFileManager
from getS3FolderPrefix import get_s3_folder_prefix

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

IG_resolver: ImageGroupResolver = None


# region shells
#  These are the entry points. See setup.py, which configures 'manifestfromS3' and 'manifestforwork:main' as console
# entry points
def main():
    """
    reads the first argument of the command line and pass it as filename to the manifestForList function
    """
    # manifestForList('RIDs.txt') # uncomment to test locally
    manifestShell()


def manifestShell():
    """
    Prepares args for running
    :return:
    """
    args = prolog()
    manifestForList(args)


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


# region Argparse
class VMBArgs:
    """
    instantiates command line argument container
    """
    pass

def prolog() -> VMBArgs:
    # Skip noisy exceptions
    import sys
    from pathlib import Path
    global shell_logger, IG_resolver
    # sys.tracebacklimit = 0
    sys.excepthook = exception_handler

    args = VMBArgs()
    parse_args(args)
    shell_logger = AOLogger(__name__, args.log_level, Path(args.log_parent))
    IG_resolver = ImageGroupResolver(args.source_container, args.image_folder_name)

    return args


def parse_args(arg_namespace: object) -> None:
    """
    :rtype: object
    :param arg_namespace. VMBArgs class which holds arg values
    """

    _parser = argparse.ArgumentParser(description="Prepares an inventory of image dimensions",
                                      usage="%(prog)s sourcefile.")

    _parser.add_argument("-d", "--debugLevel", dest='log_level', action='store',
                         choices=['info', 'warning', 'error', 'debug', 'critical'], default='info',
                         help="choice values are from python logging module")

    _parser.add_argument("-l", "--logDir", dest='log_parent', action='store', default='/tmp',
                         help="Path to log file directory")

    _parser.add_argument("-c", '--checkImageInternals', dest='check_image_internals', action='store_true',
                          help="Check image internals (slower)")

    from DBAppParser import mustExistDirectory
    _parser.add_argument("-s", '--source-container', dest='source_container', action='store', type=mustExistDirectory,
                         required=True,
                         help="container for all workRID archives")

    _parser.add_argument("-i", '--image-folder-name', dest='image_folder_name', action='store',
                         default="images", help="name of parent folder of images")

    #
    # sourceFile only used in manifestForList
    _parser.add_argument('work_list_file', help="File containing one RID per line.", nargs='?', type=argparse.FileType('r'))
    _parser.add_argument('-p', '--poll-interval', dest='poll_interval', help="Seconds between alerts for file.",
                         required=False, default=60, type=int)
    # noinspection PyTypeChecker
    _parser.parse_args(namespace=arg_namespace)


# region

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
        pass

def manifestForList(args: VMBArgs):
    """
    reads a file containing a list of work RIDs and iterate the manifestForWork function on each.
    The file can be of a format the developer like, it doesn't matter much (.txt, .csv or .json)
    :param: args
    """
    global shell_logger

    if args.work_list_file is None:
        raise ValueError("Usage: manifestforwork sourceFile where sourceFile contains a list of work RIDs")

    with args.work_list_file as f:
        for work_rid in f.readlines():
            work_rid = work_rid.strip()
            try:
                manifestForWork(args, work_rid)
            except Exception as inst:
                shell_logger.error(f"{work_rid} failed to build manifest {type(inst)} {inst.args} {inst} ")


def manifestForWork(args: VMBArgs, workRID):
    """
    this function generates the manifests for each volume of a work RID (example W22084)
    """

    global shell_logger

    vol_infos: [] = getVolumeInfos(workRID)
    if len(vol_infos) == 0:
        shell_logger.error(f"Could not find image groups for {workRID}")
        return

    for vi in vol_infos:

        complete_path: Path =  IG_resolver.full_path(workRID, vi.imageGroupID)
        uploadManifest(manifestForVolume(complete_path, vi),args)


def manifestForVolume( vol_path: Path, vi: object ) ->[]:
    """
    this function generates the manifest for an image group of a work (example: I0886 in W22084)
    :param vol_path: Path to images in a volume
    :type vol_path: Path
    :param vi: list of volume infos
    :type vi: object
    :returns: data for each image in one volume
    """

    global shell_logger
    if manifestExists(vol_path):
        shell_logger.info(f"manifest exists: {workRID}-{vi.imageGroupID} path :{s3_folder_prefix}:")
    return generateManifest(vol_path, vi.image_list)


def gzip_str(string_):
    # taken from https://gist.github.com/Garrett-R/dc6f08fc1eab63f94d2cbb89cb61c33d
    out = io.BytesIO()

    with gzip.GzipFile(fileobj=out, mode='w') as fo:
        fo.write(string_.encode())

    bytes_obj = out.getvalue()
    return bytes_obj


def uploadManifest(manifestObject: [], context: VMBArgs):
    """
    inspire from:
    https://github.com/buda-base/drs-deposit/blob/2f2d9f7b58977502ae5e90c08e77e7deee4c470b/contrib/tojsondimensions.py#L68

    in short:
       - make a compressed json string (no space)
       - gzip it
       - copy to destination
    """

    global shell_logger

    manifest_str = json.dumps(manifestObject)
    manifest_gzip = gzip_str(manifest_str)

    key = s3folderPrefix + 'dimensions.json'
    shell_logger.debug("writing " + key)
    try:
        bucket.put_object(Key=key, Body=manifest_gzip,
                          Metadata={'ContentType': 'application/json', 'ContentEncoding': 'gzip'},
                          Bucket=S3_SOURCE_BUCKET)
        shell_logger.info("wrote " + key)
    except ClientError:
        shell_logger.warn(f"Couldn't write json {key}")


def manifestExists(image_folder: Path):
    """
    Has the manifest been built yet?
    :param image_folder: parent folder of manifest
    :type image_folder: object
    """
    return  Path(image_folder,'dimensions.json').exists()


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


def fillData(image_path: str, imgdata: str):
    """
    :param image_path: full path to file to open
    :param imgdata: output string
    :param workRID: identifier for output bucket
    :param imageGroupID:
    :return:
    """
    with open(image_path, "rb") as image_file:
        image_buffer = io.BytesIO(image_file.read())
        fillDataWithBlobImage(image_buffer, imgdata)


def fillDataWithBlobImage(blob, data):
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


def generateManifest(ig_container: Path, image_list: []) -> []:
    """
    this actually generates the manifest. See example in the repo. The example corresponds to W22084, image group I0886.
    :param ig_container: path of parent of image group
    :param image_list: list of image names
    :returns: list of  internal data for each file in image_list
    """

    res = []

    image_file_name: object
    for image_file_name in image_list:
        image_path: Path = Path(ig_container,image_file_name)
        imgdata = {"filename": image_file_name}
        res.append(imgdata)
        fillData( image_path, imgdata)
    return res


def getVolumeInfos(workRid: str) -> []:
    """
    Tries data sources for image group info. If BUDA_IMAGE_GROUP global is set, prefers
    BUDA source, tries eXist on BUDA fail.
    :type workRid: str
    :param workRid: Work identifier
    :return: VolList[imagegroup1..imagegroupn]
    """
    from VolumeInfoBuda import VolumeInfoBUDA
    from VolumeInfoeXist import VolumeInfoeXist
    session = boto3.session.Session(region_name='us-east-1')
    boto_client = session.client('s3')
    dest_bucket = session.resource('s3').Bucket(S3_DEST_BUCKET)

    vol_infos: [] = []
    if BUDA_IMAGE_GROUP:
        vol_infos = (VolumeInfoBUDA(boto_client, dest_bucket)).fetch(workRid)

    if len(vol_infos) == 0:
        vol_infos = (VolumeInfoeXist(boto_client, dest_bucket)).fetch(workRid)

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
    main()  # #   manifestFromS3()
