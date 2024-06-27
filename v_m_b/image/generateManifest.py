# downloading region
import io
import logging
import sys
from pathlib import PurePath, Path

import PIL
import aiofiles
from PIL import Image


IMG_JPG='JPEG'
IMG_TIF='TIFF'
JPG_EXT= 'JPG'
TIF_EXT= 'TIF'

# The keys are the image file types as extracted from the blob

# The values are lists of possible file extension which correspond to the key
# to those lists
BUDA_supported_file_exts: {} = {IMG_JPG : [IMG_JPG, JPG_EXT], IMG_TIF :[IMG_TIF, TIF_EXT]}


def is_BUDA_Matching_file_ext(file_name: str, image_data_format: str) -> bool:
    """
    Returns true if the incoming file name is in BUDAs oo
    :param file_name: name of file to test (to provide suffix)
    :param image_data_format: from internal image data- what the file thinks it is.
    :return:
    """

    if not image_data_format or not file_name:
        return False

    # is the given format supported at all?
    if image_data_format not in BUDA_supported_file_exts.keys():
        return False

    file_suffix = Path(file_name).suffix.upper()[1:]


    # Is the extension in one of the lists of the supported types?
    matches:[] = [ x for x in BUDA_supported_file_exts[image_data_format] if x.upper() == file_suffix]
    return len(matches) > 0


async def generateManifest_a(ig_container: PurePath) -> []:
    """
    this actually generates the manifest. See example in the repo. The example corresponds to W22084, image group I0886.
    :param ig_container: path of parent of image group
    :param image_list: list of image names
    :returns: list of  internal data for each file in image_list
    """
    res: [] = []
    import os
    for image_file in os.scandir(ig_container):
        if not image_file.is_file():
            continue
        try:
            imgdata = {"filename": image_file.name}
            res.append(imgdata)
            # extracted from fillData
            async with aiofiles.open(image_file.path, "rb") as image_io:
                image_buffer: bytes = await image_io.read()
                bio: io.BytesIO = io.BytesIO(image_buffer)
                fillDataWithBlobImage(bio, imgdata)
        except:
            si = sys.exc_info()
            logging.error(f"processing {image_file.path} async file processing {si[0]} {si[1]} ")
    return res


def generateManifest_s(ig_container: PurePath) -> []:
    """
    this actually generates the manifest. See example in the repo. The example corresponds to W22084, image group I0886.
    :param ig_container: path of parent of image group
    :param image_list: list of image names
    :returns: list of  internal data for each file in image_list
    """

    res: [] = []
    import os
    for image_file in os.scandir(ig_container):
        if not image_file.is_file():
            continue
        try:
            imgdata = {"filename": image_file.name}
            res.append(imgdata)
            # extracted from fillData
            with open(str(image_file.path), "rb") as image_io:
                image_buffer = image_io.read()
                # image_buffer = io.BytesIO(image_io.read())
                fillDataWithBlobImage(io.BytesIO(image_buffer), imgdata)
        except:
            si = sys.exc_info()
            logging.error(f"processing {image_file.path} async file processing {si[0]} {si[1]} ")
    return res



def fillDataWithBlobImage(blob: io.BytesIO, data: dict):
    """
    This function populates a dict containing image data about an image
    the image is the binary blob returned by s3, an image library should be used to treat it
    please do not use the file system (saving as a file and then having the library read it)

    For pilmode, see
    https://pillow.readthedocs.io/en/5.1.x/handbook/concepts.html#concept-modes

    They are different from the Java ones:
    https://docs.oracle.com/javase/8/docs/api/java/awt/image/BufferedImage.html

    but they should be enough. Note that there's no 16 bit
    """
    size = blob.getbuffer().nbytes
    try:
        im = Image.open(blob)
        data["width"] = im.width
        data["height"] = im.height

        # jimk volume_manifest_builder #52
        if not is_BUDA_Matching_file_ext(data["filename"], im.format):
            data["format"] = im.format
            # Part of archive-ops-607 asked for this.
            # Will emit one of the COMPRESSION_INFO enums in https://pillow.readthedocs.io/en/stable/_modules/PIL/TiffImagePlugin.html
            if (data["format"] == IMG_TIF) & ("compression" in im.info.keys()):
                data["compression"] = im.info["compression"]

        # debian PIL casts these to floats, and debian JSON can't dump them to string
        data["dpi"] = [int(x) for x in im.info['dpi']] if 'dpi' in im.info.keys() else []

        # we indicate sizes of the more than 1MB
        if size > 1000000:
            data["size"] = size
    except PIL.UnidentifiedImageError:
        data["error"] = "UnidentifiedImageError"
# end region
