# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2007-2009 Async Open Source <http://www.async.com.br>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., or visit: http://www.gnu.org/.
##
## Author(s): Stoq Team <stoq-devel@async.com.br>
##

""" This module test all class in stoq/domain/receiving.py """

__tests__ = 'stoqlib/domain/receiving.py'

from decimal import Decimal
from kiwi.currency import currency

from stoqlib.domain.test.domaintest import DomainTest
from stoqlib.database.runtime import get_current_branch
from stoqlib.domain.payment.method import PaymentMethod
from stoqlib.domain.payment.payment import Payment
from stoqlib.domain.product import ProductStockItem, Storable


class TestReceivingOrder(DomainTest):

    def test_get_total(self):
        order = self.create_receiving_order()
        self.create_receiving_order_item(order)
        self.assertEqual(order.get_total(), currency(1000))

        order.discount_value = 10
        self.assertEqual(order.get_total(), currency(990))
        order.purchase.discount_value = 5
        self.assertEqual(order.get_total(), currency(985))
        order.purchase.surcharge_value = 8
        order.surcharge_value = 15
        self.assertEqual(order.get_total(), currency(1008))
        order.ipi_total = 10
        self.assertEqual(order.get_total(), currency(1018))
        order.freight_total = 6
        self.assertEqual(order.get_total(), currency(1024))
        order.secure_value = 6
        self.assertEqual(order.get_total(), currency(1030))
        order.expense_value = 12
        self.assertEqual(order.get_total(), currency(1042))

        order.purchase.status = order.purchase.ORDER_PENDING
        order.purchase.confirm()
        order.confirm()
        self.assertEqual(order.invoice_total, order.get_total())

    def test_confirm(self):
        order = self.create_receiving_order()
        order.quantity = 8
        order_item = self.create_receiving_order_item(order)
        order_item.quantity_received = 10
        self.assertRaises(ValueError, order.confirm)
        order_item.quantity_received = 8
        self.assertRaises(ValueError, order.confirm)
        self.assertRaises(ValueError, order.confirm)

        storable = order_item.sellable.product_storable
        stock_item = storable.get_stock_item(branch=order.branch, batch=None)
        for item in order.purchase.get_items():
            item.quantity_received = 0
        order.purchase.status = order.purchase.ORDER_PENDING
        self.assertEquals(stock_item.quantity, 8)
        order.purchase.confirm()
        order.confirm()
        installment_count = order.payments.count()
        for pay in order.payments:
            self.assertEqual(pay.value,
                             order.get_total() / installment_count)
            self.assertEqual(pay.value,
                             order.get_total() / installment_count)
        self.assertEqual(order.invoice_total, order.get_total())
        self.assertEquals(stock_item.quantity, 16)

    def test_order_receive_sell(self):
        product = self.create_product()
        storable = Storable(product=product, store=self.store)
        self.failIf(self.store.find(ProductStockItem, storable=storable).one())
        purchase_order = self.create_purchase_order()
        purchase_item = purchase_order.add_item(product.sellable, 1)
        purchase_order.status = purchase_order.ORDER_PENDING
        method = PaymentMethod.get_by_name(self.store, u'money')
        method.create_payment(Payment.TYPE_OUT,
                              purchase_order.group, purchase_order.branch,
                              purchase_order.get_purchase_total())
        purchase_order.confirm()

        receiving_order = self.create_receiving_order(purchase_order)
        receiving_order.branch = get_current_branch(self.store)
        self.create_receiving_order_item(
            receiving_order=receiving_order,
            sellable=product.sellable,
            purchase_item=purchase_item,
            quantity=1)
        self.failIf(self.store.find(ProductStockItem, storable=storable).one())
        receiving_order.confirm()
        product_stock_item = self.store.find(ProductStockItem,
                                             storable=storable).one()
        self.failUnless(product_stock_item)
        self.assertEquals(product_stock_item.quantity, 1)

        sale = self.create_sale()
        sale.add_sellable(product.sellable)
        sale.order()
        method = PaymentMethod.get_by_name(self.store, u'check')
        method.create_payment(Payment.TYPE_IN, sale.group, sale.branch, Decimal(100))
        sale.confirm()
        self.assertEquals(product_stock_item.quantity, 0)

    def test_update_payment_values(self):
        order = self.create_receiving_order()
        self.create_receiving_order_item(order)
        self.assertEqual(order.get_total(), currency(1000))

        for item in order.purchase.get_items():
            item.quantity_received = 0
        order.purchase.status = order.purchase.ORDER_PENDING
        order.purchase.confirm()

        installment_count = order.payments.count()
        payment_dict = {}
        for pay in order.payments:
            self.assertEqual(pay.value,
                             order.get_total() / installment_count)
            payment_dict[pay] = pay.value

        order.discount_value = 20
        order.surcharge_value = 100
        order.freight_total = 10
        order.secure_value = 15
        order.expense_value = 5
        order.update_payments()

        for pay in order.payments:
            self.assertEqual(pay.value, order.get_total() / installment_count)
            self.failIf(pay.value <= payment_dict[pay])

    def test_update_payment_values_with_freight_payment(self):
        order = self.create_receiving_order()
        self.create_receiving_order_item(order)
        self.assertEqual(order.get_total(), currency(1000))

        for item in order.purchase.get_items():
            item.quantity_received = 0
        order.purchase.status = order.purchase.ORDER_PENDING
        order.purchase.confirm()

        installment_count = order.payments.count()
        payment_dict = {}
        for pay in order.payments:
            self.assertEqual(pay.value,
                             order.get_total() / installment_count)
            payment_dict[pay] = pay.value

        order.discount_value = 20
        order.surcharge_value = 100
        order.freight_total = 10
        order.secure_value = 15
        order.expense_value = 5
        order.update_payments(create_freight_payment=True)

        for pay in order.payments:
            if pay not in payment_dict.keys():
                self.assertEqual(pay.value, order.freight_total)
            else:
                self.failIf(pay.value <= payment_dict[pay])

    def test_receiving_with_cif_freight(self):
        from stoqlib.domain.purchase import PurchaseOrder
        from stoqlib.domain.receiving import ReceivingOrder
        purchase = self.create_purchase_order()
        purchase.freight_type = PurchaseOrder.FREIGHT_CIF

        order = self.create_receiving_order(purchase_order=purchase)
        self.assertEqual(order.guess_freight_type(),
                         ReceivingOrder.FREIGHT_CIF_UNKNOWN)

        purchase.expected_freight = 10
        order = self.create_receiving_order(purchase_order=purchase)
        self.assertEqual(order.guess_freight_type(),
                         ReceivingOrder.FREIGHT_CIF_INVOICE)

    def test_get_transporter_name(self):
        receiving_order = self.create_receiving_order()

        # Without transporter, the transporter name should be empty
        receiving_order.transporter = None
        name = receiving_order.get_transporter_name()
        self.assertEqual(name, '')

        # Now there is a transporter...
        transporter = self.create_transporter(u'Juca')
        receiving_order.transporter = transporter
        name = receiving_order.get_transporter_name()
        self.assertEqual(name, u'Juca')

    def test_get_supplier_name(self):
        receiving_order = self.create_receiving_order()

        # Without supplier, the supplier name should be empty
        receiving_order.supplier = None
        name = receiving_order.get_supplier_name()
        self.assertEqual(name, '')

        # With a supplier 'test'
        transporter = self.create_supplier(u'test')
        receiving_order.supplier = transporter
        name = receiving_order.get_supplier_name()
        self.assertEqual(name, u'test')

    def test_get_percentage_value(self):
        sellable = self.create_sellable()
        sellable.cost = Decimal('35')
        receiving_order = self.create_receiving_order()
        ro = receiving_order._get_percentage_value(None)
        self.assertEqual(currency(0), ro)

        self.create_receiving_order_item(receiving_order, quantity=1,
                                         sellable=sellable)
        self.assertEqual(receiving_order._get_percentage_value(5),
                         Decimal('1.75'))

    def test_set_discount_by_percentage(self):
        sellable = self.create_sellable()
        sellable.cost = Decimal('190')
        receiving_order = self.create_receiving_order()
        self.create_receiving_order_item(receiving_order, quantity=1,
                                         sellable=sellable)

        receiving_order.discount_percentage = Decimal('10')
        self.assertEqual(receiving_order.discount_value, Decimal('19'))

    def test_get_discount_by_percentage(self):
        sellable = self.create_sellable()
        sellable.cost = Decimal('220')

        receiving_order = self.create_receiving_order()
        receiving_order.discount_value = 22
        with self.assertRaises(AssertionError):
            receiving_order._get_discount_by_percentage()

        self.create_receiving_order_item(receiving_order, quantity=1,
                                         sellable=sellable)

        self.assertEqual(receiving_order.discount_percentage, 10)

    def test_set_surcharge_by_percentage(self):
        sellable = self.create_sellable()
        sellable.cost = Decimal('200')
        receiving_order = self.create_receiving_order()
        self.create_receiving_order_item(receiving_order, quantity=1,
                                         sellable=sellable)

        receiving_order.surcharge_percentage = Decimal('10')
        self.assertEqual(receiving_order.surcharge_value, Decimal('20'))

    def test_get_surcharge_by_percentage(self):
        sellable = self.create_sellable()
        sellable.cost = Decimal('210')

        receiving_order = self.create_receiving_order()
        receiving_order.surcharge_value = 42
        with self.assertRaises(AssertionError):
            receiving_order._get_surcharge_by_percentage()

        self.create_receiving_order_item(receiving_order, quantity=2,
                                         sellable=sellable)

        self.assertEqual(receiving_order.surcharge_percentage, 10)


class TestReceivingOrderItem(DomainTest):

    def test_get_remaining_quantity(self):
        order_item = self.create_receiving_order_item()
        self.assertEqual(order_item.get_remaining_quantity(), 8)
        self.assertNotEqual(order_item.get_remaining_quantity(), 4)
        self.assertNotEqual(order_item.get_remaining_quantity(), 5)
        self.assertNotEqual(order_item.get_remaining_quantity(), 18)
        self.assertNotEqual(order_item.get_remaining_quantity(), 0)

        order_item.purchase_item.quantity_received = 7
        self.assertEqual(order_item.get_remaining_quantity(), 1)
        self.assertNotEqual(order_item.get_remaining_quantity(), 5)
        self.assertNotEqual(order_item.get_remaining_quantity(), 8)

        order_item.purchase_item.quantity_received = 8
        self.assertEqual(order_item.get_remaining_quantity(), 0)
        self.assertNotEqual(order_item.get_remaining_quantity(), 1)
        self.assertNotEqual(order_item.get_remaining_quantity(), 8)
