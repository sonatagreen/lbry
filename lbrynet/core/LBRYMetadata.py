import json

from copy import deepcopy
from lbrynet.conf import CURRENCIES
from lbrynet.core import utils
import logging

log = logging.getLogger(__name__)

BITTREX_FEE = 0.0025

# Metadata version
SOURCE_TYPES = ['lbry_sd_hash', 'url', 'btih']
NAME_ALLOWED_CHARSET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0987654321-'
BASE_METADATA_FIELDS = ['title', 'description', 'author', 'language', 'license', 'content-type', 'sources']
OPTIONAL_METADATA_FIELDS = ['thumbnail', 'preview', 'fee', 'contact', 'pubkey']

MV001 = "0.0.1"
MV002 = "0.0.2"
CURRENT_METADATA_VERSION = MV002

METADATA_REVISIONS = {}
METADATA_REVISIONS[MV001] = {'required': BASE_METADATA_FIELDS, 'optional': OPTIONAL_METADATA_FIELDS}
METADATA_REVISIONS[MV002] = {'required': ['nsfw', 'ver'], 'optional': ['license_url']}

# Fee version
BASE_FEE_FIELDS = ['amount', 'address']

FV001 = "0.0.1"
CURRENT_FEE_REVISION = FV001

FEE_REVISIONS = {}
FEE_REVISIONS[FV001] = {'required': BASE_FEE_FIELDS, 'optional': []}


def verify_name_characters(name):
    for c in name:
        assert c in NAME_ALLOWED_CHARSET, "Invalid character"
    return True


class LBRYFeeValidator(dict):
    def __init__(self, fee_dict):
        dict.__init__(self)
        assert len(fee_dict) == 1
        self.fee_version = None
        self.currency_symbol = None

        fee_to_load = deepcopy(fee_dict)

        for currency in fee_dict:
            self._verify_fee(currency, fee_to_load)

        self.amount = self._get_amount()
        self.address = self[self.currency_symbol]['address']

    def _get_amount(self):
        amt = self[self.currency_symbol]['amount']
        if isinstance(amt, float):
            return amt
        else:
            try:
                return float(amt)
            except TypeError:
                log.error('Failed to convert %s to float', amt)
                raise

    def _verify_fee(self, currency, f):
        # str in case someone made a claim with a wierd fee
        assert currency in CURRENCIES, "Unsupported currency: %s" % str(currency)
        self.currency_symbol = currency
        self.update({currency: {}})
        for version in FEE_REVISIONS:
            self._load_revision(version, f)
            if not f:
                self.fee_version = version
                break
        assert f[self.currency_symbol] == {}, "Unknown fee keys: %s" % json.dumps(f.keys())

    def _load_revision(self, version, f):
        for k in FEE_REVISIONS[version]['required']:
            assert k in f[self.currency_symbol], "Missing required fee field: %s" % k
            self[self.currency_symbol].update({k: f[self.currency_symbol].pop(k)})
        for k in FEE_REVISIONS[version]['optional']:
            if k in f[self.currency_symbol]:
                self[self.currency_symbol].update({k: f[self.currency_symbol].pop(k)})


class Metadata(dict):
    @classmethod
    def load_from_hex(cls, metadata):
        return cls(json.loads(metadata.decode('hex')))

    def __init__(self, metadata):
        dict.__init__(self)
        self.meta_version = None
        metadata_to_load = deepcopy(metadata)

        self._verify_sources(metadata_to_load)
        self._verify_metadata(metadata_to_load)

    def _load_revision(self, version, metadata):
        for k in METADATA_REVISIONS[version]['required']:
            assert k in metadata, "Missing required metadata field: %s" % k
            self.update({k: metadata.pop(k)})
        for k in METADATA_REVISIONS[version]['optional']:
            if k == 'fee':
                self._load_fee(metadata)
            elif k in metadata:
                self.update({k: metadata.pop(k)})

    def _load_fee(self, metadata):
        if 'fee' in metadata:
            self['fee'] = LBRYFeeValidator(metadata.pop('fee'))

    def _verify_sources(self, metadata):
        assert "sources" in metadata, "No sources given"
        for source in metadata['sources']:
            assert source in SOURCE_TYPES, "Unknown source type"

    def _verify_metadata(self, metadata):
        for version in METADATA_REVISIONS:
            self._load_revision(version, metadata)
            if not metadata:
                self.meta_version = version
                if utils.version_is_greater_than(self.meta_version, "0.0.1"):
                    assert self.meta_version == self['ver'], "version mismatch"
                break
        assert metadata == {}, "Unknown metadata keys: %s" % json.dumps(metadata.keys())

    def serialize(self):
        return json.dumps(self).encode("hex")

    def as_json(self):
        return json.dumps(self)
