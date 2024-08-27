"""
shell for manifest builder
"""
import json

import sys
import time
import traceback

# from manifestCommons import prolog, getVolumeInfos, gzip_str, VMT_BUDABOM
import v_m_b.manifestCommons as Common
from util_lib.AOLogger import AOLogger
from v_m_b.ImageRepository.ImageRepositoryBase import ImageRepositoryBase

MANIFEST_OBJECT_ = """
    inspire from:
    https://github.com/buda-base/drs-deposit/blob/2f2d9f7b58977502ae5e90c08e77e7deee4c470b/contrib/tojsondimensions.py#L68

    in short:
       - make a compressed json string (no space)
       - gzip it
       - send it to the repo
      :param work_rid:˚
      :param image_group_name:
      :param manifest_object:
    """

USE_RETURN_ = """
    Create and upload a manifest for an image group, given a work_rid and a specific set of VolInfos.
    Used in ao_workflows
    :param work_rid: Work Resource
    :param image_group: Specific image group to process
    :param repo: Repository to use
    :param logger: logger to use
    :return:
    """

image_repo: ImageRepositoryBase
shell_logger: AOLogger


def manifestShell():
    """
    Prepares args for running using command line or file system input
    :return:
    """
    global image_repo, shell_logger
    args, image_repo, shell_logger = Common.prolog()


    # sanity check specific to fs args: -w or -f has to be given
    if args.work_list_file is None and args.work_rid is None:
        raise ValueError("Error: in fs mode, one of -w/--work_rid or -f/--work_list_file must be given")

    all_well = manifestForList(args.work_list_file) \
        if args.work_list_file is not None \
        else doOneManifest(args.work_rid, args.image_group)
    if not all_well:
        error_string = f"Some builds failed. See log file {shell_logger.log_file_name}"
        print(error_string)
        shell_logger.hush = True  # we were just leaving anyway. Errors are already logged and sent
        raise Exception(error_string)


def manifestForList(sourceFile) -> bool:
    """
    reads a file containing a list of work RIDs and iterate the manifestForWork function on each.
    The file can be of a format the developer like, it doesn't matter much (.txt, .csv or .json)
    :param sourceFile: Openable object of input text
    :type sourceFile: Typing.TextIO
    """

    global shell_logger

    if sourceFile is None:
        raise ValueError("Usage: manifestforwork [ options ] -w sourceFile {fs | s3} [ command_options ]. "
                         "See manifestforwork -h")

    all_well: bool = True
    with sourceFile as f:
        for work_rid in f.readlines():
            work_rid = work_rid.strip()
            all_well &= doOneManifest(work_rid)
    return all_well


def doOneManifest(work_rid: str, named_image_groups:[str] = None) -> bool:
    """
    this function generates the manifests for each volume of a work RID (example W22084)
    :type work_rid: object
    """

    global image_repo, shell_logger

    is_success: bool = False

    try:
        vol_infos:[] = named_image_groups if named_image_groups is not None else Common.getVolumeInfos(work_rid, image_repo)
        if len(vol_infos) == 0:
            shell_logger.error(f"Could not find image groups for {work_rid}")
            return is_success

        for vi in vol_infos:
            upload_volume(work_rid, vi, image_repo, shell_logger)

        is_success = True
    except Exception as inst:
        eek = sys.exc_info()
        stack: str = ""
        for tb in traceback.format_tb(eek[2], 5):
            stack += tb
        shell_logger.error(f"{work_rid} failed to build manifest {type(inst)} {inst}\n{stack} ")
        is_success = False

    return is_success


def upload_volume(work_rid: str, image_group: str, repo: ImageRepositoryBase, logger: AOLogger) -> bool:
    _tick = time.monotonic()
    manifest = repo.generateManifest(work_rid, image_group)
    if len(manifest) > 0:
        upload(work_rid, image_group, manifest, repo)
        _et = time.monotonic() - _tick
        logger.info(f"Volume {work_rid}-{image_group} processing: {_et:05.3} sec ")
    else:
        _et = time.monotonic() - _tick
        logger.info(f"No manifest created for {work_rid}-{image_group} ")

    return True


def upload(work_rid: str, image_group_name: str, manifest_object: object, image_repo: ImageRepositoryBase):

    # for adict in manifest_object:
    #     print(f" dict: {adict} json: d{json.dumps(adict)}")
    manifest_str = json.dumps(manifest_object)
    # Even for debug, this is a little excessive
    # shell_logger.debug(manifest_str)
    manifest_gzip: bytes = Common.gzip_str(manifest_str)
    image_repo.uploadManifest(work_rid, image_group_name, Common.VMT_DIM, manifest_gzip)


if __name__ == '__main__':
    manifestShell()

