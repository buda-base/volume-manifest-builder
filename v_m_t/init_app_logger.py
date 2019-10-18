import logging
from pathlib import Path

def init_app_logger(loglevel: str):
    """
    app global start up logger. All app libraries use
    import logging

    my_log = logging.get_logger(__name__)
    to emit
    <time> <__name__>-LEVEL: message
    :param loglevel: string rep of python logging level
    :type loglevel: str
    :return:
    """
    from os import getpid
    from datetime import datetime
    from logging.handlers import RotatingFileHandler

    now: datetime = datetime.now()

    instance_id = f"{now.year}-{now.month}-{now.day}_{now.hour}_{now.minute}_{getpid()}"

    log_file_path: Path = Path(f"/var/log/VolumeManifestTool/{instance_id}")

    main_handler = RotatingFileHandler(log_file_path,maxBytes=4096000,backupCount=100)

    log_num_level: int = (getattr(logging, loglevel.upper(), logging.INFO))
    logging.basicConfig(format='%(asctime)s:%(name)s-%(levelname)s: %(message)s',level=log_num_level,handlers=[main_handler])

    # create formatter and add it to the handlers
    # formatter = logging.Formatter()
    #
    # # Nothing fancy, just rotating log handler
    #
    # main_handler.setFormatter(formatter)
    # main_handler.setLevel(log_num_level)
    #
    # # This should be the parent of all loggers
    # logging.getLogger('').addHandler(main_handler)

    for quiet_logger in ['boto', 'botocore', 'boto3', 'requests', 'urllib3', 'request', 's3transfer']:
        ql = logging.getLogger(quiet_logger)
        ql.setLevel(logging.CRITICAL)
        ql.propagate = True
