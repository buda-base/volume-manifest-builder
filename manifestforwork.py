#!/usr/bin/env python3

import sys
from collections import namedtuple
from urllib import request
import hashlib
import io
import json
import gzip
import os
import csv

from threading import Lock

import boto3
import botocore
from PIL import Image

from s3transfer.subscribers import BaseSubscriber
from boto3.s3.transfer import S3Transfer
from s3customtransfer import S3CustomTransfer

csvlock = Lock()

S3BUCKET = "archive.tbrc.org"

#os.environ['AWS_SHARED_CREDENTIALS_FILE'] = "/etc/buda/volumetool/credentials"

def report_error(csvwriter, csvline):
   """
   write the error in a synchronous way
   """
   global csvlock
   lock.acquire()
   csvwriter.writerow(csvline)
   lock.release()

def main():
    """
    reads the first argument of the command line and pass it as filename to the manifestForList function
    """
    # manifestForList('RIDs.txt') # uncomment to test locally
    manifestForList(sys.argv[1])


def manifestForList(filename):
    """
    reads a file containing a list of work RIDs and iterate the manifestForWork function on each.
    The file can be of a format the developer like, it doesn't matter much (.txt, .csv or .json)
    """
    session = boto3.session.Session(region_name='us-east-1')
    client = session.client('s3')
    bucket = session.resource('s3').Bucket(S3BUCKET)
    with open("errors.csv", 'w+', newline='') as csvf:
        csvwriter = csv.writer(csvf, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        with open(filename, 'r') as f:
            for workRID in f.readlines():
                workRID = workRID.strip()
                manifestForWork(client, bucket, workRID, csvwriter)


def manifestForWork(client, bucket, workRID, csvwriter):
    """
    this function generates the manifests for each volume of a work RID (example W22084)
    """
    volumeInfos = getVolumeInfos(workRID)
    for vi in volumeInfos:
        manifestForVolume(client, bucket, workRID, vi, csvwriter)


def manifestForVolume(client, bucket, workRID, vi, csvwriter):
    """
    this function generates the manifest for an image group of a work (example: I0886 in W22084)
    """
    s3folderPrefix = getS3FolderPrefix(workRID, vi.imageGroupID)
    if manifestExists(client, s3folderPrefix):
        print("manifest exists: "+workRID+"-"+vi.imageGroupID)
        #return
    manifest = generateManifest(bucket, client, s3folderPrefix, vi.imageList, csvwriter)
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
    manifest_str = json.dumps(manifestObject)
    manifest_gzip = gzip_str(manifest_str)

    key = s3folderPrefix + 'dimensions.json'
    print("writing "+key)
    bucket.put_object(Key=key, Body=manifest_gzip, Metadata={'ContentType': 'application/json', 'ContentEncoding': 'gzip'}, Bucket=S3BUCKET)


def getS3FolderPrefix(workRID, imageGroupID):
    """
    gives the s3 prefix (~folder) in which the volume will be present.
    inpire from https://github.com/buda-base/buda-iiif-presentation/blob/master/src/main/java/io/bdrc/iiif/presentation/ImageInfoListService.java#L73
    Example:
       - workRID=W22084, imageGroupID=I0886
       - result = "Works/60/W22084/images/W22084-0886/
    where:
       - 60 is the first two characters of the md5 of the string W22084
       - 0886 is:
          * the image group ID without the initial "I" if the image group ID is in the form I\d\d\d\d
          * or else the full image group ID (incuding the "I")
    """
    md5 = hashlib.md5(str.encode(workRID))
    two = md5.hexdigest()[:2]

    pre, rest = imageGroupID[0], imageGroupID[1:]
    if pre == 'I' and rest.isdigit() and len(rest) == 4:
        suffix = rest
    else:
        suffix = imageGroupID

    return 'Works/{two}/{RID}/images/{RID}-{suffix}/'.format(two=two, RID=workRID, suffix=suffix)


def manifestExists(client, s3folderPrefix):
    """
    make sure s3folderPrefix+"/dimensions.json" doesn't exist in S3
    """
    key = s3folderPrefix + 'dimensions.json'
    try:
        client.head_object(Bucket=S3BUCKET, Key=key)
        return True
    except botocore.exceptions.ClientError as exc:
        if exc.response['Error']['Code'] == '404':
            return False
        else:
            raise


def expandImageList(imageListString):
    """
    expands an image list string into an array. Image lists are documented on http://purl.bdrc.io/ontology/core/imageList
    see also this example in Java (although probably a bit too sophisticated):
    https://github.com/buda-base/buda-iiif-presentation/blob/d64a2c47c056bfa8658c06c1cddd2566ff4a0a2a/src/main/java/io/bdrc/iiif/presentation/models/ImageListIterator.java
    Example:
       - imageListString="I2PD44320001.tif:2|I2PD44320003.jpg"
       - result ["I2PD44320001.tif","I2PD44320002.tif","I2PD44320003.jpg"]
    """
    imageList = []
    spans = imageListString.split('|')
    for s in spans:
        if ':' in s:
            name, count = s.split(':')
            dot = name.find('.')
            prefix, num, ext = name[:dot-4], name[dot-4:dot], name[dot:]
            for i in range(int(count)):
                incremented = str(int(num) + i).zfill(len(num))
                imageList.append('{}{}{}'.format(prefix, incremented, ext))
        else:
            imageList.append(s)

    return imageList


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
    def __init__(self, filename, imgdata, csvwriter, s3imageKey):
        self._filename = filename
        self._imgdata = imgdata
        self._csvwriter = csvwriter
        self._s3imageKey = s3imageKey

    def __call__(self):
        fillDataWithBlobImage(self._filename, self._imgdata, self._csvwriter, self._s3imageKey)
        

def fillData(bucket, client, transfer, s3imageKey, csvwriter, imgdata):
    filename = io.BytesIO()
    print("start transfer of "+s3imageKey)
    try:
        transfer.download_file(S3BUCKET, s3imageKey, filename, callback=DoneCallback(filename, imgdata, csvwriter, s3imageKey))
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            csvline = [s3imageKey, "", "", "", "", "", "", "keydoesnotexist"]
            report_error(csvwriter, csvline)
        else:
            raise

def generateManifest(bucket, client, s3folderPrefix, imageListString, csvwriter):
    """
    this actually generates the manifest. See example in the repo. The example corresponds to W22084, image group I0886.
    """
    res = []
    transfer = S3CustomTransfer(client)
    i = 0
    for imageFileName in expandImageList(imageListString):
        i += 1
        s3imageKey = s3folderPrefix + imageFileName
        imgdata = {"filename": imageFileName}
        res.append(imgdata)
        fillData(bucket, client, transfer, s3imageKey, csvwriter, imgdata)
        #if i > 3:
        #    break

    print("begin waiting")
    transfer.wait()
    print("finish waiting")
    return res


def fillDataWithBlobImage(blob, data, csvwriter, s3imageKey):
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
    data["pilmode"] = im.mode
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
        if final4 != ".tif" and final4 != "tiff":
            errors.append("extformatmismatch")
    elif im.format == "JPEG":
        if final4 != ".jpg" and final4 != "jpeg":
            errors.append("extformatmismatch")
    else:
        errors.append("invalidformat")
    # in case of an uncompressed raw, im.info.compression == "raw"
    if errors:
        csvline = [s3imageKey, im.width, im.height, im.mode, im.format, im.palette, compression, "-".join(errors)]
        report_error(csvwriter, csvline)
    print(data)

def getVolumeInfos(workRID):
    """
    this uses the LDS-PDI capabilities to get the volume list of a work, including, for each volume:
    - image list
    - image group ID

    The information should be fetched (in csv or json) from lds-pdi, query for W22084 for instance is:
    http://purl.bdrc.io/query/Work_ImgList?R_RES=bdr:W22084&format=csv&profile=simple&pageSize=500
    """
    VolInfo = namedtuple('VolInfo', ['imageList', 'imageGroupID'])
    vol_info = []
    req = 'http://purl.bdrc.io/query/Work_ImgList?R_RES=bdr:{}&format=csv&profile=simple&pageSize=500'.format(workRID)
    with request.urlopen(req) as response:
        info = response.read()
        info = info.decode('utf8').strip()
        for line in info.split('\n')[1:]:
            _, l, g = line.replace('"', '').split(',')
            vi = VolInfo(l, g)
            vol_info.append(vi)

    return vol_info


if __name__ == '__main__':
    main()
