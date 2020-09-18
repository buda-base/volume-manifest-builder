"""
shell for manifest builder
"""
import json
import logging
import sys
import time
import traceback

# from manifestCommons import prolog, getVolumeInfos, gzip_str, VMT_BUDABOM
import v_m_b.manifestCommons as Common
from v_m_b.AOLogger import AOLogger
from v_m_b.ImageRepository.ImageRepositoryBase import ImageRepositoryBase
from v_m_b.VolumeInfo.VolInfo import VolInfo

image_repo: ImageRepositoryBase
shell_logger: AOLogger


def manifestFromS3():
    """
    Retrieves processes S3 objects in a bucket/key pair, where key is a prefix
    :return:
    """

    global image_repo, shell_logger
    args, image_repo, shell_logger = Common.prolog()

    while True:
        try:

            import boto3
            session = boto3.session.Session(region_name='us-east-1')
            client = session.client('s3')
            work_list = Common.buildWorkListFromS3(client)

            for s3Path in work_list:
                s3_full_path = f'{Common.processing_prefix}{s3Path}'

                # jimk: need to pass a file-like object. NamedTemporaryFile returns an odd
                # beast which you cant run readlines() on
                from tempfile import NamedTemporaryFile
                file_path = NamedTemporaryFile()
                client.download_file(Common.S3_MANIFEST_WORK_LIST_BUCKET, s3_full_path, file_path.name)
                manifestForList(open(file_path.name, "r"))
                # manifestForList(file_path.name)

            # don't need to rename work_list. Only when moving from src to done
            if len(work_list) > 0:
                Common.s3_work_manager.mark_done(work_list, work_list)
        except Exception as eek:
            shell_logger.log(logging.ERROR, str(eek))
        time.sleep(abs(args.poll_interval))


def manifestShell():
    """
    Prepares args for running
    :return:
    """
    global image_repo, shell_logger
    args, image_repo, shell_logger = Common.prolog()

    manifestForList(args.work_list_file)


def manifestForList(sourceFile):
    """
    reads a file containing a list of work RIDs and iterate the manifestForWork function on each.
    The file can be of a format the developer like, it doesn't matter much (.txt, .csv or .json)
    :param sourceFile: Openable object of input text
    :type sourceFile: Typing.TextIO
    """

    global shell_logger

    if sourceFile is None:
        raise ValueError("Usage: manifestforwork [ options ] sourceFile {fs | s3} [ command_options ]. "
                         "See manifestforwork -h")

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
        manifest = image_repo.generateManifest(workRID, vi)
        upload(workRID, vi.imageGroupID, manifest)
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
    # manifestFromS3()
    # manifestFromList
    # manifestFor
