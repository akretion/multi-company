# Copyright 2022 Akretion France (http://www.akretion.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests.common import Form

from odoo.addons.account_invoice_inter_company.tests.test_inter_company_invoice import (
    TestAccountInvoiceInterCompanyBase,
)


class TestAccountPaymentOrderInterCompany(TestAccountInvoiceInterCompanyBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Payment mode in company B
        cls.payment_mode_company_b = cls.env["account.payment.mode"].create(
            {
                "name": "Test Credit Transfer to Suppliers",
                "company_id": cls.company_b.id,
                "bank_account_link": "variable",
                "payment_method_id": cls.env.ref(
                    "account.account_payment_method_manual_out"
                ).id,
            }
        )
        # Payment mode in company A
        cls.payment_mode_company_a = cls.env["account.payment.mode"].create(
            {
                "name": "Test Direct Debit of customers",
                "company_id": cls.company_a.id,
                "bank_account_link": "variable",
                "payment_method_id": cls.env.ref(
                    "account.account_payment_method_manual_in"
                ).id,
            }
        )
        # Banks for Company B
        cls.partner_bank_company_b = cls.env["res.partner.bank"].create(
            {
                "acc_number": "123456789",
                "partner_id": cls.company_b.partner_id.id,
                "company_id": False,
            }
        )
        cls.bank_journal_company_b.write(
            {"bank_account_id": cls.partner_bank_company_b.id}
        )
        # Banks for Company A
        cls.partner_bank_company_a = cls.env["res.partner.bank"].create(
            {
                "acc_number": "987654321",
                "partner_id": cls.company_a.partner_id.id,
                "company_id": False,
            }
        )
        cls.bank_journal_company_a.write(
            {"bank_account_id": cls.partner_bank_company_a.id}
        )
        # Supplier Invoice in Company B
        cls.invoice_company_b = Form(
            cls.account_move_obj.with_company(cls.company_b.id).with_context(
                default_move_type="in_invoice",
            )
        )
        cls.invoice_company_b.partner_id = cls.partner_company_a
        cls.invoice_company_b.invoice_date = cls.invoice_company_b.date
        cls.invoice_company_b.journal_id = cls.purchases_journal_company_b
        cls.invoice_company_b.currency_id = cls.env.ref("base.EUR")

        with cls.invoice_company_b.invoice_line_ids.new() as line_form:
            line_form.product_id = cls.product_consultant_multi_company
            line_form.quantity = 1
            line_form.product_uom_id = cls.env.ref("uom.product_uom_hour")
            line_form.account_id = cls.a_expense_company_b
            line_form.name = "Service Multi Company"
            line_form.price_unit = 450.0
        cls.invoice_company_b = cls.invoice_company_b.save()
        cls.invoice_line_b = cls.invoice_company_b.invoice_line_ids[0]

        cls.company_b.invoice_auto_validation = True

        cls.product_b = cls.invoice_line_b.product_id
        cls.product_b.with_company(
            cls.company_a.id
        ).property_account_income_id = cls.a_sale_company_a.id

    def _create_intercompany_supplier_invoice(self):
        # Confirm the customer invoice in company A
        self.invoice_company_a.with_user(self.user_company_a.id).with_context(
            test_queue_job_no_delay=True
        ).action_post()
        # Search supplier invoice created in company B
        invoice_company_b = self.account_move_obj.with_user(
            self.user_company_b.id
        ).search(
            [
                ("auto_invoice_id", "=", self.invoice_company_a.id),
                ("company_id", "=", self.company_b.id),
            ],
            limit=1,
        )
        return invoice_company_b

    def _create_intercompany_customer_invoice(self):
        # Confirm the supplier invoice in company B
        self.invoice_company_b.with_user(self.user_company_b.id).with_context(
            test_queue_job_no_delay=True
        ).action_post()
        # Search customer invoice created in company A
        invoice_company_a = self.account_move_obj.with_user(
            self.user_company_a.id
        ).search(
            [
                ("auto_invoice_id", "=", self.invoice_company_b.id),
                ("company_id", "=", self.company_a.id),
            ],
            limit=1,
        )
        return invoice_company_a

    def _create_payment_order(
        self, invoice, journal, payment_mode, payment_type, company
    ):
        # Update payment_mode in invoice
        invoice.write({"payment_mode_id": payment_mode.id})
        # Create payment order
        self.env["account.invoice.payment.line.multi"].with_context(
            active_model="account.move", active_ids=invoice.ids
        ).create({}).run()
        payment_order = self.env["account.payment.order"].search(
            [
                ("state", "=", "draft"),
                ("payment_type", "=", payment_type),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        # Update journal in payment order
        payment_order.write({"journal_id": journal.id})
        # Update communication in payment lines
        for payment_line in payment_order.payment_line_ids:
            payment_line.write({"communication": invoice.name})
        return payment_order

    def _upload_payment_order(self, payment_order):
        # Confirm payment order
        payment_order.draft2open()
        payment_order.open2generated()
        payment_order.generated2uploaded()

    def _pay_invoice(self, invoice, journal, payment_mode, payment_type, company):
        payment_order = self._create_payment_order(
            invoice, journal, payment_mode, payment_type, company
        )
        self._upload_payment_order(payment_order)
        return payment_order

    def _pay_invoice_company_b(self, invoice):
        return self._pay_invoice(
            invoice,
            self.bank_journal_company_b,
            self.payment_mode_company_b,
            "outbound",
            self.company_b,
        )

    def _pay_invoice_company_a(self, invoice):
        return self._pay_invoice(
            invoice,
            self.bank_journal_company_a,
            self.payment_mode_company_a,
            "inbound",
            self.company_a,
        )

    def _create_two_installment_term(self):
        return self.env["account.payment.term"].create(
            {
                "name": "30% now, 70% in 30 days",
                "line_ids": [
                    (0, 0, {"value": "percent", "value_amount": 30.0, "days": 0}),
                    (0, 0, {"value": "balance", "days": 30}),
                ],
            }
        )

    def _create_supplier_invoice_with_installments(
        self, on_customer_invoice=True, on_supplier_invoice=True
    ):
        term = self._create_two_installment_term()
        if on_customer_invoice:
            with Form(
                self.invoice_company_a.with_company(self.company_a)
            ) as invoice_form:
                invoice_form.invoice_payment_term_id = term
        if on_supplier_invoice:
            self.partner_company_a.with_company(
                self.company_b
            ).property_supplier_payment_term_id = term
        return self._create_intercompany_supplier_invoice()

    def _get_installments(self, invoice):
        return (
            invoice.sudo()
            .line_ids.filtered(
                lambda line: line.account_internal_type in ("receivable", "payable")
            )
            .sorted("date_maturity")
        )

    def _set_other_receivable_property_company_a(self):
        self.partner_company_b.with_company(
            self.company_a
        ).property_account_receivable_id = self.account_obj.create(
            {
                "code": "X4112.A",
                "name": "Other receivable - (Company A)",
                "user_type_id": self.env.ref("account.data_account_type_receivable").id,
                "reconcile": True,
                "company_id": self.company_a.id,
            }
        )

    def _create_payment_order_without_line(self, payment_mode, journal):
        return (
            self.env["account.payment.order"]
            .with_company(payment_mode.company_id)
            .create(
                {
                    "payment_mode_id": payment_mode.id,
                    "payment_type": payment_mode.payment_type,
                    "journal_id": journal.id,
                }
            )
        )

    def _upload_unlinked_misc_entry(
        self, payment_mode, bank_journal, misc_journal, accounts, partner, balance
    ):
        partner_account, other_account = accounts
        misc_move = self.account_move_obj.with_company(payment_mode.company_id).create(
            {
                "move_type": "entry",
                "journal_id": misc_journal.id,
                "date": "2026-01-15",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": partner_account.id,
                            "partner_id": partner.id,
                            "debit": max(balance, 0.0),
                            "credit": max(-balance, 0.0),
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": other_account.id,
                            "debit": max(-balance, 0.0),
                            "credit": max(balance, 0.0),
                        },
                    ),
                ],
            }
        )
        misc_move.action_post()
        payment_order = self._create_payment_order_without_line(
            payment_mode, bank_journal
        )
        misc_move.line_ids.filtered(
            lambda line: line.account_id == partner_account
        ).create_payment_line_from_move_line(payment_order)
        payment_order.payment_line_ids.communication = "Misc entry"
        self._upload_payment_order(payment_order)
        return payment_order

    def _assert_unreconciled_message_posted(self, payment_order):
        auto_move = payment_order.payment_ids.auto_move_id
        communication = payment_order.payment_line_ids[0].communication
        self.assertTrue(
            payment_order.message_ids.filtered(
                lambda message: auto_move.name in (message.body or "")
                and communication in message.body
            )
        )

    def test_create_customer_invoice_and_pay_supplier_invoice(self):
        # Create intercompany supplier invoice in company B
        invoice_company_b = self._create_intercompany_supplier_invoice()
        # Pay supplier invoice in company B
        self._pay_invoice(
            invoice_company_b,
            self.bank_journal_company_b,
            self.payment_mode_company_b,
            "outbound",
            self.company_b,
        )
        # Check payment state of supplier invoice in company B
        self.assertEqual(invoice_company_b.payment_state, "paid")
        # Check payment state of customer invoice in company A
        self.assertEqual(self.invoice_company_a.payment_state, "paid")

    def test_create_customer_invoice_and_pay_customer_invoice(self):
        # Create intercompany supplier invoice in company B
        invoice_company_b = self._create_intercompany_supplier_invoice()
        # Pay customer invoice in company A
        self._pay_invoice(
            self.invoice_company_a,
            self.bank_journal_company_a,
            self.payment_mode_company_a,
            "inbound",
            self.company_a,
        )
        # Check payment state of customer invoice in company A
        self.assertEqual(self.invoice_company_a.payment_state, "paid")
        # Check payment state of supplier invoice in company B
        self.assertEqual(invoice_company_b.payment_state, "paid")

    def test_create_supplier_invoice_and_pay_supplier_invoice(self):
        # Create intercompany customer invoice in company A
        invoice_company_a = self._create_intercompany_customer_invoice()
        # Pay supplier invoice in company B
        self._pay_invoice(
            self.invoice_company_b,
            self.bank_journal_company_b,
            self.payment_mode_company_b,
            "outbound",
            self.company_b,
        )
        # Check payment state of supplier invoice in company B
        self.assertEqual(self.invoice_company_b.payment_state, "paid")
        # Check payment state of customer invoice in company A
        self.assertEqual(invoice_company_a.payment_state, "paid")

    def test_create_supplier_invoice_and_pay_customer_invoice(self):
        # Create intercompany customer invoice in company A
        invoice_company_a = self._create_intercompany_customer_invoice()
        # Pay customer invoice in company A
        self._pay_invoice(
            invoice_company_a,
            self.bank_journal_company_a,
            self.payment_mode_company_a,
            "inbound",
            self.company_a,
        )
        # Check payment state of customer invoice in company A
        self.assertEqual(invoice_company_a.payment_state, "paid")
        # Check payment state of supplier invoice in company B
        self.assertEqual(self.invoice_company_b.payment_state, "paid")

    def test_create_customer_invoice_and_pay_customer_invoice_with_draft_supplier_invoice(
        self,
    ):
        # Inactive automatic validation so supplier invoice will be draft
        self.company_b.invoice_auto_validation = False
        # Create intercompany supplier invoice in company B
        self._create_intercompany_supplier_invoice()
        # Pay customer invoice in company A
        payment_order = self._pay_invoice(
            self.invoice_company_a,
            self.bank_journal_company_a,
            self.payment_mode_company_a,
            "inbound",
            self.company_a,
        )
        # Check payment state of customer invoice in company A
        self.assertEqual(self.invoice_company_a.payment_state, "paid")
        self.assertTrue(payment_order.payment_ids.auto_move_id)
        self.assertFalse(
            payment_order.payment_ids.auto_move_id.line_ids.full_reconcile_id
        )
        self._assert_unreconciled_message_posted(payment_order)

    def test_cancel_payment_order(self):
        invoice_company_a = self._create_intercompany_customer_invoice()
        # Pay customer invoice in company A
        payment_order = self._pay_invoice(
            invoice_company_a,
            self.bank_journal_company_a,
            self.payment_mode_company_a,
            "inbound",
            self.company_a,
        )
        auto_move = payment_order.payment_ids.auto_move_id
        payment_order.action_cancel()
        self.assertEqual(auto_move.state, "cancel")
        payment_order.cancel2draft()
        payment_order.draft2open()
        self.assertFalse(payment_order.payment_ids.auto_move_id)

    def test_mirror_move_fields(self):
        invoice_company_b = self._create_intercompany_supplier_invoice()
        payment_order = self._pay_invoice_company_b(invoice_company_b)
        payment = payment_order.payment_ids
        auto_move = payment.auto_move_id
        self.assertEqual(auto_move.company_id, self.company_a)
        self.assertEqual(auto_move.journal_id, self.bank_journal_company_a)
        self.assertEqual(auto_move.ref, payment.payment_reference)
        self.assertEqual(auto_move.date, payment.date)
        outstanding_line = auto_move.line_ids.filtered(
            lambda line: line.account_id
            == self.bank_journal_company_a.payment_debit_account_id
        )
        self.assertEqual(outstanding_line.debit, payment.amount)

    def test_mirror_account_from_linked_line(self):
        invoice_company_b = self._create_intercompany_supplier_invoice()
        linked_line = self._get_installments(self.invoice_company_a)
        self._set_other_receivable_property_company_a()
        payment_order = self._pay_invoice_company_b(invoice_company_b)
        mirror_line = payment_order.payment_ids.auto_move_id.line_ids.filtered(
            lambda line: line.reconciled
        )
        self.assertEqual(mirror_line.account_id, linked_line.account_id)
        self.assertEqual(mirror_line.full_reconcile_id, linked_line.full_reconcile_id)

    def test_mirror_unlinked_outbound_line_on_receivable_property(self):
        payment_order = self._upload_unlinked_misc_entry(
            self.payment_mode_company_b,
            self.bank_journal_company_b,
            self.misc_journal_company_b,
            (self.a_pay_company_b, self.a_expense_company_b),
            self.partner_company_a,
            -300.0,
        )
        mirror_line = payment_order.payment_ids.auto_move_id.line_ids.filtered(
            lambda line: line.credit
        )
        self.assertEqual(
            mirror_line.account_id,
            self.partner_company_b.with_company(
                self.company_a
            ).property_account_receivable_id,
        )
        self.assertFalse(mirror_line.reconciled)
        self._assert_unreconciled_message_posted(payment_order)

    def test_mirror_unlinked_inbound_line_on_payable_property(self):
        payment_order = self._upload_unlinked_misc_entry(
            self.payment_mode_company_a,
            self.bank_journal_company_a,
            self.misc_journal_company_a,
            (self.a_recv_company_a, self.a_sale_company_a),
            self.partner_company_b,
            300.0,
        )
        mirror_line = payment_order.payment_ids.auto_move_id.line_ids.filtered(
            lambda line: line.debit
        )
        self.assertEqual(
            mirror_line.account_id,
            self.partner_company_a.with_company(
                self.company_b
            ).property_account_payable_id,
        )
        self.assertFalse(mirror_line.reconciled)
        self._assert_unreconciled_message_posted(payment_order)

    def test_payment_line_without_journal_item_has_no_linked_invoice(self):
        payment_order = self._create_payment_order_without_line(
            self.payment_mode_company_b, self.bank_journal_company_b
        )
        self.env["account.payment.line"].create(
            {
                "order_id": payment_order.id,
                "partner_id": self.partner_company_a.id,
                "partner_bank_id": self.partner_bank_company_a.id,
                "amount_currency": 200.0,
                "currency_id": self.company_b.currency_id.id,
                "communication": "Without journal item",
            }
        )
        self.assertTrue(
            self.account_move_obj.search(
                [
                    ("auto_invoice_id", "=", False),
                    ("company_id", "=", self.company_a.id),
                ],
                limit=1,
            )
        )
        self._upload_payment_order(payment_order)
        mirror_line = payment_order.payment_ids.auto_move_id.line_ids.filtered(
            lambda line: line.credit
        )
        self.assertEqual(
            mirror_line.account_id,
            self.partner_company_b.with_company(
                self.company_a
            ).property_account_receivable_id,
        )
        self.assertEqual(mirror_line.partner_id, self.partner_company_b)
        self.assertFalse(mirror_line.reconciled)
        self._assert_unreconciled_message_posted(payment_order)

    def test_pay_customer_invoice_with_cancelled_supplier_invoice(self):
        self.company_b.invoice_auto_validation = False
        invoice_company_b = self._create_intercompany_supplier_invoice()
        invoice_company_b.sudo().button_cancel()
        payment_order = self._pay_invoice_company_a(self.invoice_company_a)
        self.assertEqual(self.invoice_company_a.payment_state, "paid")
        auto_move = payment_order.payment_ids.auto_move_id
        self.assertEqual(auto_move.state, "posted")
        self.assertFalse(auto_move.line_ids.full_reconcile_id)
        self._assert_unreconciled_message_posted(payment_order)

    def test_pay_both_installments_in_one_order(self):
        self.payment_mode_company_b.default_date_prefered = "now"
        invoice_company_b = self._create_supplier_invoice_with_installments()
        dest_installments = self._get_installments(self.invoice_company_a)
        self.assertEqual(len(dest_installments), 2)
        payment_order = self._pay_invoice_company_b(invoice_company_b)
        self.assertEqual(len(payment_order.payment_ids), 1)
        self.assertEqual(invoice_company_b.payment_state, "paid")
        self.assertEqual(self.invoice_company_a.payment_state, "paid")
        mirror_lines = payment_order.payment_ids.auto_move_id.line_ids
        for dest_installment in dest_installments:
            mirror_line = (
                mirror_lines & dest_installment.full_reconcile_id.reconciled_line_ids
            )
            self.assertEqual(mirror_line.credit, dest_installment.debit)

    def test_pay_second_installment_only(self):
        invoice_company_b = self._create_supplier_invoice_with_installments()
        first_installment, second_installment = self._get_installments(
            self.invoice_company_a
        )
        payment_order = self._create_payment_order(
            invoice_company_b,
            self.bank_journal_company_b,
            self.payment_mode_company_b,
            "outbound",
            self.company_b,
        )
        first_paid_installment = self._get_installments(invoice_company_b)[0]
        payment_order.payment_line_ids.filtered(
            lambda line: line.move_line_id == first_paid_installment
        ).unlink()
        self._upload_payment_order(payment_order)
        self.assertTrue(second_installment.reconciled)
        self.assertFalse(first_installment.matched_credit_ids)

    def test_dest_with_more_installments_left_unreconciled_on_linked_account(self):
        invoice_company_b = self._create_supplier_invoice_with_installments(
            on_supplier_invoice=False
        )
        self.assertEqual(len(self._get_installments(invoice_company_b)), 1)
        self.assertEqual(len(self._get_installments(self.invoice_company_a)), 2)
        linked_account = self._get_installments(self.invoice_company_a).account_id
        self._set_other_receivable_property_company_a()
        payment_order = self._pay_invoice_company_b(invoice_company_b)
        self.assertEqual(invoice_company_b.payment_state, "paid")
        self.assertFalse(self.invoice_company_a.line_ids.matched_credit_ids)
        auto_move = payment_order.payment_ids.auto_move_id
        self.assertFalse(auto_move.line_ids.full_reconcile_id)
        mirror_line = auto_move.line_ids.filtered("credit")
        self.assertEqual(mirror_line.account_id, linked_account)
        self.assertEqual(mirror_line.partner_id, self.partner_company_b)
        self._assert_unreconciled_message_posted(payment_order)

    def test_payer_with_more_installments_left_unreconciled_on_linked_account(self):
        self.payment_mode_company_b.default_date_prefered = "now"
        invoice_company_b = self._create_supplier_invoice_with_installments(
            on_customer_invoice=False
        )
        self.assertEqual(len(self._get_installments(invoice_company_b)), 2)
        self.assertEqual(len(self._get_installments(self.invoice_company_a)), 1)
        linked_account = self._get_installments(self.invoice_company_a).account_id
        self._set_other_receivable_property_company_a()
        payment_order = self._pay_invoice_company_b(invoice_company_b)
        self.assertEqual(invoice_company_b.payment_state, "paid")
        self.assertFalse(self.invoice_company_a.line_ids.matched_credit_ids)
        auto_move = payment_order.payment_ids.auto_move_id
        self.assertFalse(auto_move.line_ids.full_reconcile_id)
        mirror_lines = auto_move.line_ids.filtered("credit")
        self.assertEqual(len(mirror_lines), 2)
        self.assertEqual(
            sum(mirror_lines.mapped("credit")), self.invoice_company_a.amount_total
        )
        self.assertEqual(mirror_lines.account_id, linked_account)
        self._assert_unreconciled_message_posted(payment_order)

    def test_installment_already_paid_left_unreconciled(self):
        self.payment_mode_company_b.default_date_prefered = "now"
        invoice_company_b = self._create_supplier_invoice_with_installments()
        first_installment, second_installment = self._get_installments(
            self.invoice_company_a
        )
        other_payment = self.account_move_obj.with_company(self.company_a).create(
            {
                "move_type": "entry",
                "date": "2026-01-15",
                "journal_id": self.misc_journal_company_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": first_installment.account_id.id,
                            "partner_id": first_installment.partner_id.id,
                            "credit": first_installment.debit,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": self.a_sale_company_a.id,
                            "debit": first_installment.debit,
                        },
                    ),
                ],
            }
        )
        other_payment.action_post()
        (
            first_installment
            | other_payment.line_ids.filtered(
                lambda line: line.account_id == first_installment.account_id
            )
        ).reconcile()
        payment_order = self._pay_invoice_company_b(invoice_company_b)
        self.assertEqual(invoice_company_b.payment_state, "paid")
        self.assertTrue(second_installment.reconciled)
        self.assertEqual(
            first_installment.matched_credit_ids.credit_move_id.move_id, other_payment
        )
        self._assert_unreconciled_message_posted(payment_order)

    def test_linked_invoice_of_another_company_left_unreconciled(self):
        invoice_company_b = self._create_intercompany_supplier_invoice()
        linked_invoice = self.invoice_company_a
        other_move = self.account_move_obj.with_company(self.company_b).create(
            {
                "move_type": "entry",
                "date": "2026-01-15",
                "journal_id": self.misc_journal_company_b.id,
            }
        )
        self.company_b.intercompany_invoice_lock = False
        invoice_company_b.sudo().auto_invoice_id = other_move
        payment_order = self._pay_invoice_company_b(invoice_company_b)
        self.assertEqual(invoice_company_b.payment_state, "paid")
        self.assertFalse(linked_invoice.line_ids.matched_credit_ids)
        mirror_line = payment_order.payment_ids.auto_move_id.line_ids.filtered(
            lambda line: line.credit
        )
        self.assertEqual(
            mirror_line.account_id,
            self.partner_company_b.with_company(
                self.company_a
            ).property_account_receivable_id,
        )
        self.assertFalse(mirror_line.reconciled)
        self._assert_unreconciled_message_posted(payment_order)

    def test_missing_bank_journal(self):
        invoice_company_b = self._create_intercompany_supplier_invoice()
        payment_order = self._create_payment_order(
            invoice_company_b,
            self.bank_journal_company_b,
            self.payment_mode_company_b,
            "outbound",
            self.company_b,
        )
        payment_order.payment_line_ids.partner_bank_id = self.env[
            "res.partner.bank"
        ].create(
            {
                "acc_number": "444555666",
                "partner_id": self.partner_company_a.id,
                "company_id": False,
            }
        )
        with self.assertRaisesRegex(UserError, "No bank journal"):
            self._upload_payment_order(payment_order)

    def test_missing_outstanding_account(self):
        invoice_company_b = self._create_intercompany_supplier_invoice()
        self.bank_journal_company_a.payment_debit_account_id = False
        with self.assertRaisesRegex(UserError, "No outstanding account"):
            self._pay_invoice_company_b(invoice_company_b)

    def test_partner_without_company(self):
        supplier = self.env["res.partner"].create({"name": "External supplier"})
        supplier_bank = self.env["res.partner.bank"].create(
            {"acc_number": "111222333", "partner_id": supplier.id, "company_id": False}
        )
        self.invoice_company_b.write(
            {"partner_id": supplier.id, "partner_bank_id": supplier_bank.id}
        )
        self.invoice_company_b.action_post()
        payment_order = self._pay_invoice_company_b(self.invoice_company_b)
        self.assertEqual(self.invoice_company_b.payment_state, "paid")
        self.assertFalse(payment_order.payment_ids.auto_move_id)

    def test_upload_by_user_of_paying_company_only(self):
        self.user_company_b.groups_id = [
            (4, self.env.ref("account_payment_order.group_account_payment").id)
        ]
        invoice_company_b = self._create_intercompany_supplier_invoice()
        payment_order = self._create_payment_order(
            invoice_company_b,
            self.bank_journal_company_b,
            self.payment_mode_company_b,
            "outbound",
            self.company_b,
        )
        self._upload_payment_order(payment_order.with_user(self.user_company_b))
        self.assertEqual(self.invoice_company_a.payment_state, "paid")
        self.assertEqual(
            payment_order.payment_ids.auto_move_id.company_id, self.company_a
        )
