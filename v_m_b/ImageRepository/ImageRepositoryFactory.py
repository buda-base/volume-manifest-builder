from v_m_b.ImageRepository.S3ImageRepository import S3ImageRepository
from v_m_b.ImageRepository.FSImageRepository import FSImageRepository


class ImageRepositoryFactory(object):
    """
    Constructs a ImageRepositoryBase object
    """

    # noinspection PyTypeChecker
    def repository(self, source: str,  **kwargs):
        """
        Construct a repository for the desired channel: s3 or file system
        See v_m_b.manifestCommons.prolog for calling sequence
        :param source: 's3' or 'fs' (case insensitive)
        :type source: str
        :type kwargs: object
        :keyword object client: boto client session
        :keyword object dest_bucket: object of destination
        :keyword str source_container: directory name of parent of works
        :keyword str image_classifier: directory name of parent of image groups
        :return:
        """
        # S3 calling args.s3, client=client, bucket=dest_bucket
        if source.lower() == "s3":
            return S3ImageRepository( client=kwargs['client'],
                                      dest_bucket=kwargs['bucket'],
                                      images_name=kwargs['image_classifier'])

        if source.lower() == "fs":
            return FSImageRepository(source_root=kwargs['source_container'],
                                     images_name=kwargs['image_classifier'])
