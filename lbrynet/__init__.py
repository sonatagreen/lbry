import logging

log = logging.getLogger(__name__)
logging.getLogger(__name__).addHandler(logging.NullHandler())
log.setLevel(logging.ERROR)

__version__ = "0.3.10"
version = tuple(__version__.split('.'))