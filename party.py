# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from sql import Null

from trytond import backend
from trytond.config import config
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction

__all__ = ['Party']

DISCOUNT_DIGITS = int(config.get('digits', 'discount_digits', 4))


class Party:
    __name__ = 'party.party'
    __metaclass__ = PoolMeta
    customer_invoice_discount = fields.Property(fields.Numeric(
            'Customer Invoice Discount', digits=(16, DISCOUNT_DIGITS), states={
                'invisible': ~Eval('context', {}).get('company'),
                }))
    supplier_invoice_discount = fields.Property(fields.Numeric(
            'Supplier Invoice Discount', digits=(16, DISCOUNT_DIGITS), states={
                'invisible': ~Eval('context', {}).get('company'),
                }))

    @classmethod
    def __register__(cls, module_name):
        pool = Pool()
        Property = pool.get('ir.property')
        TableHandler = backend.get('TableHandler')

        super(Party, cls).__register__(module_name)

        cursor = Transaction().connection.cursor()
        handler = TableHandler(cls, module_name)
        table = cls.__table__()
        # Migration from 3.4.0: moved invoice_discount to property
        # customer_invoice_discount
        if handler.column_exist('invoice_discount'):
            cursor.execute(*table.select(table.id, table.invoice_discount,
                    where=table.invoice_discount != Null))
            for party_id, invoice_discount in cursor.fetchall():
                Property.set('customer_invoice_discount', cls.__name__,
                    [party_id], ',%s' % invoice_discount.to_eng_string())
            handler.drop_column('invoice_discount', exception=True)
