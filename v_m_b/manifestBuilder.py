"""
shell for manifest builder
"""
import json
import sys
import time
import traceback
from typing import TextIO

from AOLogger import AOLogger
from VolumeInfo.VolInfo import VolInfo
# from manifestCommons import prolog, getVolumeInfos, gzip_str, VMT_BUDABOM
import manifestCommons as Common
from ImageRepository.ImageRepositoryBase import ImageRepositoryBase

image_repo: ImageRepositoryBase
shell_logger: AOLogger


def manifestShell():
    """
    Prepares args for running
    :return:
    """
    global image_repo, shell_logger
    args, image_repo, shell_logger = Common.prolog()

    manifestForList(args.work_list_file)


def manifestForList(sourceFile: str):
    """
    reads a file containing a list of work RIDs and iterate the manifestForWork function on each.
    The file can be of a format the developer like, it doesn't matter much (.txt, .csv or .json)
    :param sourceFile: Openable object of input text
    :type sourceFile: Typing.TextIO
    """

    global shell_logger

    if sourceFile is None:
        raise ValueError("Usage: manifestforwork sourceFile where sourceFile contains a list of work RIDs")

    with sourceFile as f:
        for work_rid in f.readlines():
            work_rid = work_rid.strip()
            try:
                manifestForWork(work_rid)
            except Exception as inst:
                eek = sys.exc_info()
                stack: str = ""
                for tb in traceback.format_tb(eek[2], 5):
                    stack += tb
                shell_logger.error(f"{work_rid} failed to build manifest {type(inst)} {inst}\n{stack} ")


def manifestForWork(workRID: str):
    """
    this function generates the manifests for each volume of a work RID (example W22084)
    :type workRID: object
    """

    global image_repo, shell_logger

    vol_infos: [VolInfo] = Common.getVolumeInfos(workRID, image_repo)
    if len(vol_infos) == 0:
        shell_logger.error(f"Could not find image groups for {workRID}")
        return

    for vi in vol_infos:
        _tick = time.monotonic()
        upload(workRID, vi.imageGroupID, image_repo.generateManifest(workRID, vi))
        _et = time.monotonic() - _tick
        print(f"Volume reading: {_et:05.3} ")
        shell_logger.debug(f"Volume reading: {_et:05.3} ")


def upload(work_Rid: str, image_group_name: str, manifest_object: object):
    """
    inspire from:
    https://github.com/buda-base/drs-deposit/blob/2f2d9f7b58977502ae5e90c08e77e7deee4c470b/contrib/tojsondimensions.py#L68

    in short:
       - make a compressed json string (no space)
       - gzip it
       - send it to the repo
      :param work_Rid:˚
      :param image_group_name:
      :param manifest_object:
    """
    manifest_str = json.dumps(manifest_object)
    manifest_gzip: bytes = Common.gzip_str(manifest_str)
    image_repo.uploadManifest(work_Rid, image_group_name, Common.VMT_DIM, manifest_gzip)


if __name__ == '__main__':
    manifestShell()
    # manifestFromList
    # manifestFor
