# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.config import config
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction
from sql import Null
from trytond import backend


__all__ = ['Party', 'PartyAccount']

DISCOUNT_DIGITS = (16, config.getint('product', 'price_decimal', default=4))


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'
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
    def __register__(cls, module_name):
        Property = Pool().get('ir.property')
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


    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field in {'customer_invoice_discount', 'supplier_invoice_discount'}:
            return pool.get('party.party.account')
        return super(Party, cls).multivalue_model(field)


class PartyAccount(metaclass=PoolMeta):
    __name__ = 'party.party.account'

    customer_invoice_discount = fields.Numeric(
        "Customer Invoice Discount", digits=DISCOUNT_DIGITS)
    supplier_invoice_discount = fields.Numeric(
        "Supplier Invoice Discount", digits=DISCOUNT_DIGITS)

    @classmethod
    def _migrate_property(cls, field_names, value_names, fields):
        field_names += ['customer_invoice_discount',
            'supplier_invoice_discount']
        value_names += ['customer_invoice_discount',
            'supplier_invoice_discount']
        super(PartyAccount, cls)._migrate_property(field_names, value_names,
            fields)
