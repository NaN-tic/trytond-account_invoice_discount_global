# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.config import config
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval

__all__ = ['Party', 'PartyAccount']

DISCOUNT_DIGITS = (16, config.getint('product', 'price_decimal', default=4))


class Party:
    __name__ = 'party.party'
    __metaclass__ = PoolMeta
    customer_invoice_discount = fields.MultiValue(fields.Numeric(
            'Customer Invoice Discount', digits=DISCOUNT_DIGITS,
            states={
                'invisible': ~Eval('context', {}).get('company'),
                }))
    supplier_invoice_discount = fields.MultiValue(fields.Numeric(
            'Supplier Invoice Discount', digits=DISCOUNT_DIGITS,
            states={
                'invisible': ~Eval('context', {}).get('company'),
                }))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field in {'customer_invoice_discount', 'supplier_invoice_discount'}:
            return pool.get('party.party.account')
        return super(Party, cls).multivalue_model(field)


class PartyAccount:
    __name__ = 'party.party.account'
    __metaclass__ = PoolMeta

    customer_invoice_discount = fields.Numeric(
        "Customer Invoice Discount", digits=DISCOUNT_DIGITS)
    supplier_invoice_discount = fields.Numeric(
        "Supplier Invoice Discount", digits=DISCOUNT_DIGITS)
