from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.config import config

__all__ = ['Party']

DISCOUNT_DIGITS = int(config.get('digits', 'discount_digits', 4))


class Party:
    __name__ = 'party.party'
    __metaclass__ = PoolMeta
    invoice_discount = fields.Numeric('Invoice Discount',
        digits=(16, DISCOUNT_DIGITS))
