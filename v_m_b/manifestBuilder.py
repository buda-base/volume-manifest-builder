"""
shell for manifest builder
"""
import time
from typing import TextIO

from AOLogger import AOLogger
from manifestCommons import prolog, getVolumeInfos
from ImageRepository.ImageRepositoryBase import ImageRepositoryBase

image_repo: ImageRepositoryBase
shell_logger: AOLogger


def manifestShell():
    """
    Prepares args for running
    :return:
    """
    global image_repo, shell_logger
    args, image_repo, shell_logger = prolog()

    manifestForList(args.source_container)


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
                shell_logger.error(f"{work_rid} failed to build manifest {type(inst)} {inst.args} {inst} ")


def manifestForWork(workRID: str):
    """
    this function generates the manifests for each volume of a work RID (example W22084)
    :type workRID: object
    """

    global image_repo, shell_logger

    vol_infos: [] = getVolumeInfos(workRID, image_repo)
    if len(vol_infos) == 0:
        shell_logger.error(f"Could not find image groups for {workRID}")
        return

    for vi in vol_infos:
        _tick = time.monotonic()
        image_repo.generateManifest(workRID, vi)
        _et = time.monotonic() - _tick
        print(f"Volume reading: {_et:05.3} ")
        shell_logger.debug(f"Volume reading: {_et:05.3} ")
        
        
if __name__ == '__main__':
    manifestShell()
    # manifestFromList
    # manifestFor
