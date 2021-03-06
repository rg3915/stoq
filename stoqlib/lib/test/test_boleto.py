# -*- Mode: Python; coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2011 Async Open Source <http://www.async.com.br>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., or visit: http://www.gnu.org/.
##
##  Author(s): Stoq Team <stoq-devel@async.com.br>
##

import datetime
import os
import tempfile

import unittest

from stoqlib.api import api
from stoqlib.lib.boleto import (
    BankSantander, BankBanrisul, BankBB, BankBradesco,
    BankCaixa, BankItau, BankReal, BoletoException)
from stoqlib.domain.account import BankAccount, BillOption
from stoqlib.domain.payment.method import PaymentMethod
from stoqlib.domain.test.domaintest import DomainTest
from stoqlib.lib.diffutils import diff_pdf_htmls
from stoqlib.lib.pdf import pdftohtml
from stoqlib.reporting.boleto import BillReport
from stoqlib.lib.unittestutils import get_tests_datadir


class TestBank(DomainTest):
    def setUp(self):
        DomainTest.setUp(self)
        self._filename = tempfile.mktemp(prefix="stoqlib-test-boleto-",
                                         suffix=".pdf")
        self._pdf_html = None

    def tearDown(self):
        DomainTest.tearDown(self)
        try:
            os.unlink(self._filename)
        except OSError:
            pass
        if self._pdf_html:
            try:
                os.unlink(self._pdf_html)
            except OSError:
                pass

    def _configure_boleto(self, number, account, agency, **kwargs):
        bill = PaymentMethod.get_by_name(self.store, u'bill')
        bank_account = BankAccount(account=bill.destination_account,
                                   bank_account=account,
                                   bank_branch=agency,
                                   bank_number=int(number),
                                   store=self.store)

        for key, value in kwargs.items():
            BillOption(store=self.store,
                       bank_account=bank_account,
                       option=unicode(key),
                       value=value)
        api.sysparam(self.store).BILL_INSTRUCTIONS = u'Primeia linha da instrução'

    def _get_expected(self, filename, generated):
        fname = get_tests_datadir(filename + '.pdf.html')
        if not os.path.exists(fname):
            open(fname, 'w').write(open(generated).read())
        return fname

    def _create_bill_sale(self):
        sale = self.create_sale()
        self.add_product(sale)
        sale.order()
        self.payment = self.add_payments(sale, method_type=u'bill',
                                         date=datetime.datetime(2011, 5, 30))[0]
        sale.client = self.create_client()
        address = self.create_address()
        address.person = sale.client.person
        sale.confirm()
        return sale

    def _render_bill_to_html(self, sale):
        report = BillReport(self._filename, list(sale.payments))
        report.today = datetime.date(2011, 05, 30)
        report.add_payments()
        report.override_payment_id(400)
        report.override_payment_description([u'sale XXX', u'XXX - description'])
        report.save()
        self._pdf_html = tempfile.mktemp(prefix="stoqlib-test-boleto-",
                                         suffix=".pdf.html")
        pdftohtml(self._filename, self._pdf_html)
        return self._pdf_html

    def _diff(self, sale, name):
        generated = self._render_bill_to_html(sale)
        expected = self._get_expected(name, generated)
        diff = diff_pdf_htmls(expected, generated)
        self.failIf(diff, '%s\n%s' % ("Files differ, output:", diff))

    def test_banco_do_brasil(self):
        sale = self._create_bill_sale()
        self._configure_boleto(u"001",
                               convenio=u"12345678",
                               agency=u"1172",
                               account=u"00403005")
        self._diff(sale, 'boleto-001')

    def test_banco_do_brasil_com_d_v(self):
        sale = self._create_bill_sale()
        self._configure_boleto(u"001",
                               convenio=u"12345678",
                               agency=u"1172-X",
                               account=u"00403005-X")
        self._diff(sale, 'boleto-001')

    def test_nossa_caixa(self):
        sale = self._create_bill_sale()
        self._configure_boleto(u"104",
                               agency=u"1565",
                               account=u"414-3")

        self._diff(sale, 'boleto-104')

    def test_itau(self):
        sale = self._create_bill_sale()
        self._configure_boleto(u"341",
                               account=u"13877",
                               agency=u"1565",
                               carteira=u'175')

        self._diff(sale, 'boleto-341')

    def test_bradesco(self):
        sale = self._create_bill_sale()
        self._configure_boleto(u"237",
                               account=u"029232-4",
                               agency=u"278-0",
                               carteira=u'06')

        self._diff(sale, 'boleto-237')

    def test_real(self):
        sale = self._create_bill_sale()
        self._configure_boleto(u"356",
                               account=u"5705853",
                               agency=u"0531",
                               carteira=u'06')

        self._diff(sale, 'boleto-356')


class TestBancoBanrisul(unittest.TestCase):
    def setUp(self):
        self.dados = BankBanrisul(
            agencia=u'1102',
            conta=u'9000150',
            data_vencimento=datetime.date(2000, 7, 4),
            valor_documento=550,
            nosso_numero=u'22832563',
        )

    def test_linha_digitavel(self):
        self.assertEqual(
            self.dados.linha_digitavel,
            '04192.11107 29000.150226 83256.340593 8 10010000055000'
        )

    def test_tamanho_codigo_de_barras(self):
        self.assertEqual(len(self.dados.barcode), 44)

    def test_codigo_de_barras(self):
        self.assertEqual(self.dados.barcode,
                         '04198100100000550002111029000150228325634059')

    def test_campo_livre(self):
        self.assertEqual(self.dados.campo_livre,
                         '2111029000150228325634059')

    def test_validate_field(self):
        valid = ['06.181631.0-9.',
                 '06.011.348.0-8'
                 ]
        for _ in valid:
            pass


class TestBB(unittest.TestCase):
    def setUp(self):
        d = BankBB(
            data_vencimento=datetime.date(2011, 3, 8),
            valor_documento=2952.95,
            agencia=u'9999',
            conta=u'99999',
            convenio=u'7777777',
            nosso_numero=u'87654',
        )
        self.dados = d

    def test_linha_digitavel(self):
        self.assertEqual(self.dados.linha_digitavel,
                         '00190.00009 07777.777009 00087.654182 6 49000000295295'
                         )

    def test_codigo_de_barras(self):
        self.assertEqual(self.dados.barcode,
                         '00196490000002952950000007777777000008765418'
                         )

    def test_validate_field(self):
        valid = ['0295-x',
                 '2589-5',
                 '3062-7',
                 '8041-1',
                 '15705-8',
                 '39092-5',
                 '83773-3']
        for v in valid:
            self.dados.validate_field(v)


class TestBancoBradesco(unittest.TestCase):
    def setUp(self):
        self.dados = BankBradesco(
            carteira=u'06',
            agencia=u'278-0',
            conta=u'039232-4',
            data_vencimento=datetime.date(2011, 2, 5),
            valor_documento=8280.00,
            nosso_numero=u'2125525',
        )

        self.dados2 = BankBradesco(
            carteira=u'06',
            agencia=u'1172',
            conta=u'403005',
            data_vencimento=datetime.date(2011, 3, 9),
            valor_documento=2952.95,
            nosso_numero=u'75896452',
            numero_documento=u'75896452',
        )

    def test_linha_digitavel(self):
        self.assertEqual(self.dados.linha_digitavel,
                         '23790.27804 60000.212559 25003.923205 4 48690000828000'
                         )

        self.assertEqual(self.dados2.linha_digitavel,
                         '23791.17209 60007.589645 52040.300502 1 49010000295295'
                         )

    def test_codigo_de_barras(self):
        self.assertEqual(self.dados.barcode,
                         '23794486900008280000278060000212552500392320'
                         )
        self.assertEqual(self.dados2.barcode,
                         '23791490100002952951172060007589645204030050'
                         )

    def test_agencia(self):
        self.assertEqual(self.dados.agencia, '0278-0')

    def test_conta(self):
        self.assertEqual(self.dados.conta, '0039232-4')

    def test_validate_field(self):
        valid = ['0278-0',
                 '1172',
                 '14978-0',
                 '403005',
                 '0039232-4',
                 '02752']
        for v in valid:
            self.dados.validate_field(v)

    def test_carteira(self):
        x = BankBradesco(
            carteira=u'9',
            agencia=u'02752',
            conta=u'14978-0',
            data_vencimento=datetime.date(2011, 3, 9),
            valor_documento=2952.95,
            nosso_numero=u'75896452',
            numero_documento=u'75896452')
        self.assertEquals(
            x.barcode, '23793490100002952952752090007589645200149780')

        x.validate_option(u'carteira', '9')
        x.validate_option(u'carteira', '09')
        self.assertRaises(BoletoException, x.validate_option, u'carteira', '')
        self.assertRaises(BoletoException, x.validate_option, u'carteira', 'CNR')
        self.assertRaises(BoletoException, x.validate_option, u'carteira', '-1')
        self.assertRaises(BoletoException, x.validate_option, u'carteira', '100')


class TestBancoCaixa(unittest.TestCase):
    def setUp(self):
        self.dados = BankCaixa(
            carteira=u'SR',
            agencia=u'1565',
            conta=u'414-3',
            data_vencimento=datetime.date(2011, 2, 5),
            valor_documento=355.00,
            nosso_numero=u'19525086',
        )

    def test_linha_digitavel(self):
        self.assertEqual(self.dados.linha_digitavel,
                         '10498.01952 25086.156509 00000.004143 7 48690000035500'
                         )

    def test_tamanho_codigo_de_barras(self):
        self.assertEqual(len(self.dados.barcode), 44)

    def test_codigo_de_barras(self):
        self.assertEqual(self.dados.barcode,
                         '10497486900000355008019525086156500000000414'
                         )


class TestBancoItau(unittest.TestCase):
    def setUp(self):
        self.dados = BankItau(
            carteira=u'110',
            conta=u'12345-7',
            agencia=u'0057',
            data_vencimento=datetime.date(2002, 5, 1),
            valor_documento=123.45,
            nosso_numero=u'12345678',
        )

    def test_linha_digitavel(self):
        self.assertEqual(self.dados.linha_digitavel,
                         '34191.10121 34567.880058 71234.570001 6 16670000012345'
                         )

    def test_codigo_de_barras(self):
        self.assertEqual(self.dados.barcode,
                         '34196166700000123451101234567880057123457000'
                         )


class TestBancoReal(unittest.TestCase):
    def setUp(self):
        self.dados = BankReal(
            carteira=u'06',
            agencia=u'0531',
            conta=u'5705853',
            data_vencimento=datetime.date(2011, 2, 5),
            valor_documento=355.00,
            nosso_numero=u'123',
        )

    def test_linha_digitavel(self):
        self.assertEqual(self.dados.linha_digitavel,
                         '35690.53154 70585.390001 00000.001230 8 48690000035500'
                         )

    def test_codigo_de_barras(self):
        self.assertEqual(self.dados.barcode,
                         '35698486900000355000531570585390000000000123'
                         )


class TestSantander(unittest.TestCase):
    def setUp(self):
        self.dados = BankSantander(
            agencia=u'1333',
            conta=u'0707077',
            data_vencimento=datetime.date(2012, 1, 22),
            valor_documento=2952.95,
            nosso_numero=u'1234567',
        )

    def test_linha_digitavel(self):
        self.assertEqual(self.dados.linha_digitavel,
                         '03399.07073 07700.000123 34567.901029 6 52200000295295'
                         )

    def test_tamanho_codigo_de_barras(self):
        self.assertEqual(len(self.dados.barcode), 44)

    def test_codigo_de_barras(self):
        self.assertEqual(self.dados.barcode,
                         '03396522000002952959070707700000123456790102'
                         )

if __name__ == '__main__':
    unittest.main()
