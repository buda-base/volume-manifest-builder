import argparse
import io

from S3WorkFileManager import S3WorkFileManager
from boto.s3.bucket import Bucket
from AOLogger import AOLogger
from ImageGroupResolver import ImageGroupResolver
from PIL import Image

# for writing and GetVolumeInfos
S3_DEST_BUCKET: str = "archive.tbrc.org"

# jimk Toggle legacy and new sources
BUDA_IMAGE_GROUP = True

# for manifestFromS3 and S3WorkFileManager

S3_MANIFEST_WORK_LIST_BUCKET: str = "manifest.bdrc.org"
LOG_FILE_ROOT: str = "/var/log/VolumeManifestTool"
todo_prefix: str = "processing/todo/"
processing_prefix: str = "processing/inprocess/"
done_prefix: str = "processing/done/"

s3_work_manager: S3WorkFileManager = S3WorkFileManager(S3_MANIFEST_WORK_LIST_BUCKET, todo_prefix, processing_prefix,
                                                       done_prefix)

shell_logger: AOLogger = None
IG_resolver: ImageGroupResolver = None


def fillDataWithBlobImage(blob, data):
    """
    This function populates a dict containing the height and width of the image
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

    blob2 = io.BytesIO(blob)
    size = blob2.getbuffer().nbytes
    im = Image.open(blob2)
    data["width"] = im.width
    data["height"] = im.height
    # we indicate sizes of the more than 1MB
    if size > 1000000:
        data["size"] = size


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
    from VolumeInfoBuda import VolumeInfoBUDA
    from VolumeInfoeXist import VolumeInfoeXist

    vol_infos: [] = []
    if BUDA_IMAGE_GROUP:
        vol_infos = (VolumeInfoBUDA(botoClient, bucket)).fetch(workRid)

    if len(vol_infos) == 0:
        vol_infos = (VolumeInfoeXist(botoClient, bucket)).fetch(workRid)

    return vol_infos


def report_error(csvwriter, csvline):
    """
   write the error in a synchronous way
   """
    global csvlock
    csvlock.acquire()
    csvwriter.writerow(csvline)
    csvlock.release()


def parse_args(arg_namespace: object) -> None:
    """
    :rtype: object
    :param arg_namespace. VMBArgs class which holds arg values
    """

    _parser = argparse.ArgumentParser(description="Prepares an inventory of image dimensions",
                                      usage="%(prog)s sourcefile.")

    _parser.add_argument("-d",
                         "--debugLevel",
                         dest='log_level',
                         action='store',
                         choices=['info', 'warning', 'error', 'debug', 'critical'],
                         default='info',
                         help="choice values are from python logging module")

    _parser.add_argument("-l",
                         "--logDir",
                         dest='log_parent',
                         action='store',
                         default='/tmp',
                         help="Path to log file directory")

    _parser.add_argument("-c",
                         '--checkImageInternals',
                         dest='check_image_internals',
                         action='store_true',
                         help="Check image internals (slower)")

    from DBAppParser import mustExistDirectory
    _parser.add_argument("-s",
                         '--source-container',
                         dest='source_container',
                         action='store',
                         type=mustExistDirectory,
                         required=True,
                         help="container for all workRID archives")

    _parser.add_argument("-i",
                         '--image-folder-name',
                         dest='image_folder_name',
                         action='store',
                         default="images",
                         help="name of parent folder of images")

    #
    # sourceFile only used in manifestForList
    _parser.add_argument('work_list_file',
                         help="File containing one RID per line.",
                         nargs='?',
                         type=argparse.FileType('r'))

    _parser.add_argument('-p',
                         '--poll-interval',
                         dest='poll_interval',
                         help="Seconds between alerts for file.",
                         required=False,
                         default=60,
                         type=int)

    # noinspection PyTypeChecker
    _parser.parse_args(namespace=arg_namespace)


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


def gzip_str(string_):
    # taken from https://gist.github.com/Garrett-R/dc6f08fc1eab63f94d2cbb89cb61c33d
    out = io.BytesIO()

    import gzip
    with gzip.GzipFile(fileobj=out, mode='w') as fo:
        fo.write(string_.encode())

    bytes_obj = out.getvalue()
    return bytes_obj


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
    shell_logger = AOLogger('local_v_m_b', args.log_level, Path(args.log_parent))
    IG_resolver = ImageGroupResolver(args.source_container, args.image_folder_name)

    return args
