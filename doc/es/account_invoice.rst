#:inside:account_invoice/account_invoice:bullet_list:fields#

* |invoice_discount|: Se aplicará un descuento sobre el total de la factura
  correspondiente al porcentaje indicado.

  Cuando elegimos el tercero de la factura este campo se rellena con el
  descuento por defecto que se ha indicado en la ficha del tercero.

  Este descuento se reflejará como una línea en negativo al confirmar la
  factura, y usará el producto configurado como |discount_product| en la
  configuración contable (|menu_account_configuration|).

.. |invoice_discount| field:: account.invoice/invoice_discount
.. |discount_product| field:: account.configuration/discount_product
.. |menu_account_configuration| tryref:: account.menu_account_configuration/complete_name
