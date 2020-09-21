import os
from pathlib import Path


class ImageGroupResolver(object):
    """
    Fully qualifies an image group
    """

    def __init__(self, container: str, image_classifier: str):
        self._container = container
        self._image_classifier = image_classifier

    def full_path(self, workRid: str, image_group_name: str) -> Path:
        """
        Fully qualifies a RID and a Path
        :param workRid:
        :param image_group_name:
        :return: fully qualified path to image group
        """
        v1path = Path(self._container, workRid, self._image_classifier, image_group_name)
        if not os.path.exists(v1path):
            v1path = Path(self._container, workRid, self._image_classifier, f"{workRid}-{image_group_name}")
        return v1path
