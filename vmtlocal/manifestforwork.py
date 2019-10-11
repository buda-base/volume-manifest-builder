#!/usr/bin/env python3
import argparse
import collections
import csv
import gzip
import io
import json
import os
from threading import Lock

from PIL import Image
from DBApps.DbAppParser import mustExistDirectory

# imageList is a str[], imageGroupId: str
VolInfo = collections.namedtuple('VolInfo', ['imageList', 'imageGroupID'])



# region Parser
class ArgNamespace:
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
    _parser.add_argument('-s', '--sourcedir', dest='source_dir', action='store',
                         help='parent of all work RIDs input directory', type=mustExistDirectory)
    _parser.add_argument("sourceFile", dest="rid_file", help="File containing one RID per line.")

    # noinspection PyTypeChecker
    _parser.parse_args(namespace=arg_namespace)


# endregion


#region error csv
csvlock: Lock = Lock()

first_error: bool = True
def report_error(csvwriter, csvline):
    """
    write the error in a synchronous way
    """
    global csvlock
    global first_error

    csvlock.acquire()
    if first_error:
        csvwriter.writerow(
            ["s3imageKey", "workRID", "imageGroupID", "size", "width", "height", "mode", "format", "palette",
             "compression", "errors"])
        first_error = False
    csvwriter.writerow(csvline)
    csvlock.release()
#endregion

def main():
    """
    reads the first argument of the command line and pass it as filename to the manifestForList function
    """
    # manifestForList('RIDs.txt') # uncomment to test locally
    print("starting...")
    manifestShell()


def manifestShell():
    """
    Prepares args for running
    :return:
    """
    args = ArgNamespace()
    parse_args(args)
    manifestForList(args.source_dir, args.rid_file)


def manifestForList(parent_dir: str, filename:str):
    """
    reads a file containing aand iterate the manifestForWork function on each.
    The file can be of a format the developer like, it doesn't matter much (.txt, .csv or .json)
    :param:
    :param: filename  list of work RIDs
    """

    errorsfilename = "errors-" + os.path.basename(filename) + ".csv"
    with open(errorsfilename, 'w+', newline='') as csvf:
        csvwriter = csv.writer(csvf, delimiter=',', quoting=csv.QUOTE_MINIMAL)

        with open(filename, 'r') as f:
            for work_r_i_d in f.readlines():
                work_r_i_d = work_r_i_d.strip()
                manifestForWork(parent_dir, work_r_i_d, csvwriter)


def manifestForWork(parent_dir: str, work_r_i_d, csvwriter):
    """
    this function generates the manifests for each volume of a work RID (example W22084)
    """
    vol_infos: [] = getVolumeInfos(parent_dir, work_r_i_d)
    if (len(vol_infos) == 0):
        print(f"Could not find image groups for {work_r_i_d}")
        return

    for vi in vol_infos:
        manifestForVolume(parent_dir, work_r_i_d, vi, csvwriter)


def manifestForVolume(parent: str, work_Rid: str, vi: VolInfo, csvwriter: object):
    """
    this function generates the manifest for an image group of a work (example: I0886 in W22084)
    """
    manifest = generateManifest(parent, vi.imageList, csvwriter, work_Rid, vi.imageGroupID)
    uploadManifest(parent, work_Rid, manifest)


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

    manifest_str = json.dumps(manifestObject)
    manifest_gzip = gzip_str(manifest_str)

    key = s3folderPrefix + 'dimensions.json'
    print("writing " + key)
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


def getVolumeInfos(workRid: str, parent: str) -> object:
    """
    Tries data sources for image group info. If BUDA_IMAGE_GROUP global is set, prefers
    BUDA source, tries eXist on BUDA fail.
    :type workRid: str
    :param workRid: Work identifier
    :param botoClient: handle to AWS
    :return: VolList[imagegroup1..imagegroupn]
    """

    vol_infos: VolInfo[] = []
    if BUDA_IMAGE_GROUP:
        vol_infos = (VolumeInfoBUDA(botoClient)).fetch(workRid)

    if (len(vol_infos) == 0):
        vol_infos = (VolumeInfoeXist(botoClient)).fetch(workRid)

    return vol_infos


if __name__ == '__main__':
    main()  # manifestFromS3()
