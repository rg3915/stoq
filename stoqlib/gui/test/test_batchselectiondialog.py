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

import datetime

from stoqlib.api import api
from stoqlib.gui.dialogs.batchselectiondialog import (BatchSelectionDialog,
                                                      BatchIncreaseSelectionDialog)
from stoqlib.gui.test.uitestutils import GUITest


class TestBatchSelectionDialog(GUITest):
    def test_create(self):
        storable = self.create_storable(is_batch=True)
        batch = self.create_storable_batch(storable=storable,
                                           batch_number=u'1')
        batch.create_date = datetime.date(2010, 10, 10)
        batch = self.create_storable_batch(storable=storable,
                                           batch_number=u'2')
        batch.create_date = datetime.date(2011, 11, 11)
        batch = self.create_storable_batch(storable=storable,
                                           batch_number=u'3')
        batch.create_date = datetime.date(2012, 12, 12)

        storable.register_initial_stock(10, api.get_current_branch(self.store),
                                        1, u'1')
        storable.register_initial_stock(15, api.get_current_branch(self.store),
                                        1, u'2')
        storable.register_initial_stock(8, api.get_current_branch(self.store),
                                        1, u'3')

        dialog = BatchSelectionDialog(self.store, storable, 33)
        for entry in dialog._spins.keys():
            entry.update(1)
            dialog._spins[entry].update(12)

        for entry in dialog._spins.keys()[1:]:
            entry.update(2)
            dialog._spins[entry].update(7)

        for entry in dialog._spins.keys()[2:]:
            entry.update(3)
            dialog._spins[entry].update(8)

        dialog.existing_batches_expander.set_expanded(True)

        self.check_dialog(dialog, 'dialog-batch-selection-dialog-create')


class TestBatchIncreaseSelectionDialog(GUITest):
    def test_batch_number_suggestion(self):
        branch = api.get_current_branch(self.store)
        branch.acronym = u'AB'

        storable = self.create_storable(is_batch=True)
        storable2 = self.create_storable(is_batch=True)

        dialog = BatchIncreaseSelectionDialog(self.store, storable, 10)
        self.assertEqual(dialog._last_entry.get_text(), '')

        api.sysparam(self.store).update_parameter(u'SUGGEST_BATCH_NUMBER', u'1')
        try:
            storable.register_initial_stock(1, self.create_branch(), 0,
                                            batch_number=u'123')
            dialog = BatchIncreaseSelectionDialog(self.store, storable, 10)
            # Make sure it suggested right
            self.assertEqual(dialog._last_entry.get_text(), '124')

            spinbutton = dialog.get_spin_by_entry(dialog._last_entry)
            spinbutton.update(5)
            # Updating the spinbutton should append a new entry with the suggestion
            self.assertEqual(dialog._last_entry.get_text(), '125')
            self.click(dialog.main_dialog.ok_button)

            dialog = BatchIncreaseSelectionDialog(self.store, storable2, 10)
            # Since the dialog above was confirmed on the same store this one is,
            # it should consider it's batch numbers for the next suggestion
            self.assertEqual(dialog._last_entry.get_text(), '126')
        finally:
            api.sysparam(self.store).update_parameter(u'SUGGEST_BATCH_NUMBER', u'0')

    def test_batch_number_suggestion_synchronized_mode(self):
        branch = api.get_current_branch(self.store)
        branch.acronym = u'AB'

        storable = self.create_storable(is_batch=True)
        storable2 = self.create_storable(is_batch=True)

        dialog = BatchIncreaseSelectionDialog(self.store, storable, 10)
        self.assertEqual(dialog._last_entry.get_text(), '')

        try:
            api.sysparam(self.store).update_parameter(u'SUGGEST_BATCH_NUMBER', u'1')
            # We need to do this by hand sincr update_parameter won't let us
            # update value for some parameters (SYNCHRONIZED_MODE is one of them)
            api.sysparam(self.store).SYNCHRONIZED_MODE = u'1'
            api.sysparam(self.store).rebuild_cache_for(u'SYNCHRONIZED_MODE')
            storable.register_initial_stock(1, self.create_branch(), 0,
                                            batch_number=u'130')
            dialog = BatchIncreaseSelectionDialog(self.store, storable, 10)
            # Make sure it suggested right
            self.assertEqual(dialog._last_entry.get_text(), '131-AB')

            spinbutton = dialog.get_spin_by_entry(dialog._last_entry)
            spinbutton.update(5)
            # Updating the spinbutton should append a new entry with the suggestion
            self.assertEqual(dialog._last_entry.get_text(), '132-AB')
            self.click(dialog.main_dialog.ok_button)

            dialog = BatchIncreaseSelectionDialog(self.store, storable2, 10)
            # Since the dialog above was confirmed on the same store this one is,
            # it should consider it's batch numbers for the next suggestion
            self.assertEqual(dialog._last_entry.get_text(), '133-AB')

            branch.acronym = None
            spinbutton = dialog.get_spin_by_entry(dialog._last_entry)
            # FIXME: Why is this not working? If i put a print before .update
            # and one after, I can see the traceback raises between the prints,
            # GUITest will say that there was an unhandled exception (this one)
            # and assertRaisesRegexp will say that ValueError wasn't raised. WTF???
            #with self.assertRaisesRegexp(
            #    ValueError,
            #    ("branch 'Moda Stoq' needs an acronym since we are on "
            #     "synchronized mode")):
            #    spinbutton.update(1)
        finally:
            api.sysparam(self.store).update_parameter(u'SUGGEST_BATCH_NUMBER', u'0')
            api.sysparam(self.store).SYNCHRONIZED_MODE = u'0'
            api.sysparam(self.store).rebuild_cache_for(u'SYNCHRONIZED_MODE')

    def test_batch_number_validation(self):
        storable = self.create_storable(is_batch=True)
        storable2 = self.create_storable(is_batch=True)
        self.create_storable_batch(storable=storable, batch_number=u'123')
        self.create_storable_batch(storable=storable, batch_number=u'124')

        dialog = BatchIncreaseSelectionDialog(self.store, storable2, 10)
        dialog._last_entry.update(u'123')
        self.assertInvalid(dialog, ['_last_entry'])
        dialog._last_entry.update(u'126')
        self.assertValid(dialog, ['_last_entry'])
