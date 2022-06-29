# downloading region
import io
import logging
import sys
from pathlib import PurePath, Path

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


async def generateManifest_a(ig_container: PurePath, image_list: []) -> []:
    """
    this actually generates the manifest. See example in the repo. The example corresponds to W22084, image group I0886.
    :param ig_container: path of parent of image group
    :param image_list: list of image names
    :returns: list of  internal data for each file in image_list
    """
    res: [] = []
    image_file_name: str
    for image_file_name in image_list:
        try:
            image_path: Path = Path(ig_container, image_file_name)
            imgdata = {"filename": image_file_name}
            res.append(imgdata)
            # extracted from fillData
            async with aiofiles.open(image_path, "rb") as image_file:
                image_buffer: bytes = await image_file.read()
                bio: io.BytesIO = io.BytesIO(image_buffer)
                fillDataWithBlobImage(bio, imgdata)
        except:
            si = sys.exc_info()
            logging.error(f"processing {image_file_name} async file processing {si[0]} {si[1]} ")
    return res


def generateManifest_s(ig_container: PurePath, image_list: []) -> []:
    """
    this actually generates the manifest. See example in the repo. The example corresponds to W22084, image group I0886.
    :param ig_container: path of parent of image group
    :param image_list: list of image names
    :returns: list of  internal data for each file in image_list
    """

    res = []

    image_file_name: str
    for image_file_name in image_list:
        image_path: Path = Path(ig_container, image_file_name)
        imgdata = {"filename": image_file_name}
        res.append(imgdata)
        # extracted from fillData
        with open(str(image_path), "rb") as image_file:
            image_buffer = image_file.read()
            # image_buffer = io.BytesIO(image_file.read())
            try:
                fillDataWithBlobImage(io.BytesIO(image_buffer), imgdata)
            except:
                exc = sys.exc_info()
                logging.error(f"processing {image_file_name} sync file processing {exc[0]} {exc[1]} ")
        # asyncio.run(fillData(image_path, imgdata))
    return res


def fillDataWithBlobImage(blob: io.BytesIO, data: dict):
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

    # blob2 = io.BytesIO(blob)
    # size = blob2.getbuffer().nbytes
    # im = Image.open(blob2)

    size = blob.getbuffer().nbytes
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
# end region
