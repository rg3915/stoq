# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2012 Async Open Source <http://www.async.com.br>
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
## Author(s): Stoq Team <stoq-devel@async.com.br>
##

import mock

from stoqlib.gui.editors.callseditor import CallsEditor
from stoqlib.gui.search.callsearch import CallsSearch
from stoqlib.gui.uitestutils import GUITest


class TestCallsSearch(GUITest):

    def testShow(self):
        # 2 calls, different persons
        call1 = self.create_call()
        self.create_call(attendant=call1.attendant)

        search = CallsSearch(self.trans, date=call1.date)
        search.search.refresh()
        self.check_search(search, 'calls-show')

    def testWithPerson(self):
        # 2 calls, different persons
        call1 = self.create_call()
        self.create_call(attendant=call1.attendant)

        search = CallsSearch(self.trans, person=call1.person)
        search.search.refresh()
        self.check_search(search, 'calls-show-person')

    def testActions(self):
        # 2 calls, different persons
        call1 = self.create_call()
        self.create_call(attendant=call1.attendant)

        search = CallsSearch(self.trans, date=call1.date,
                             reuse_transaction=True)
        self.assertNotSensitive(search, ['csv_button', 'print_button'])
        search.search.refresh()
        self.assertSensitive(search, ['csv_button', 'print_button'])

        self.assertNotSensitive(search._toolbar, ['edit_button'])
        selected = search.results[0]
        search.results.select(selected)
        self.assertSensitive(search._toolbar, ['edit_button'])

        with mock.patch('stoqlib.gui.search.callsearch.print_report') as print_report:
            self.click(search.print_button)
            print_report.assert_called_once()

        with mock.patch('stoqlib.gui.search.callsearch.SpreadSheetExporter.export') as export:
            self.click(search.csv_button)
            export.assert_called_once()

        with mock.patch('stoqlib.gui.search.callsearch.run_dialog') as run_dialog:
            self.click(search._toolbar.edit_button)
            run_dialog.assert_called_once()
            args, kwargs = run_dialog.call_args
            editor, parent, conn, model, person, person_type = args
            self.assertEquals(editor, CallsEditor)
            self.assertEquals(parent, search)
            self.assertEquals(model, selected.call)
            self.assertEquals(person, None)

        with mock.patch('stoqlib.gui.search.callsearch.run_dialog') as run_dialog:
            self.click(search._toolbar.new_button)
            run_dialog.assert_called_once()
            args, kwargs = run_dialog.call_args
            editor, parent, conn, model, person, person_type = args
            self.assertEquals(editor, CallsEditor)
            self.assertEquals(parent, search)
            self.assertEquals(model, None)
            self.assertEquals(person, None)
