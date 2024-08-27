import abc
import logging
import  archive_ops.api as ao_api
from v_m_b.ImageRepository.ImageRepositoryBase import ImageRepositoryBase

#
# Super magic constant.
# See https://github.com/archive-ops/scripts/processing/sync2archive.sh
#

# TODO: Extend to support a named image group
class VolumeInfoBase(metaclass=abc.ABCMeta):
    """
    Gets volume info for a work.
    Passes request off to subclasses
    """

    logger: logging = None

    def __init__(self, repo: ImageRepositoryBase):
        """
        :param boto_client: context for operations
        :type boto_client: boto3.client
        : param bucket: target container
        :type bucket: boto.s3.bucket.Bucket
        """
        self._repo = repo
        self.logger = logging.getLogger(__name__)

    @abc.abstractmethod
    def get_image_group_disk_paths(self, urlRequest) -> []:
        """
        Subclasses implement
        :param urlRequest:
        :return: [] with  one entry for each image group in the work's catalog
        """
        pass

    @staticmethod
    def getImageGroup(image_group_id: str) -> str:
        """
        :param image_group_id:
        :type image_group_id: str
        Some old image groups in eXist are encoded Innn, but their real name on disk is
        RID-nnnn. this detects their cases, and returns the disk folder they actually
        exist in. This is a stupid gross hack, we should either fix the archive repository, or have the
        BUDA and/or eXist APIs adjust for this.
        """
        return ao_api.get_image_group(image_group_id)

