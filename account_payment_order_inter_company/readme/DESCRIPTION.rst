This module allows for an inter-company billing to automatically pay the invoice in Company A as soon as the invoice in Company B is paid.

The mirror entry is booked at upload in the company receiving the payment:
one line per payment line on the account of the linked inter-company invoice,
reconciled with it, and the net amount on the outstanding receipts (or payments)
account of its bank journal.

On a multi-installment invoice, each payment line is paired with the installment
of the linked invoice at the same position, by due date.

A linked invoice of another company than the receiving one counts as no link.
A payment line without linked invoice is booked on the partner's receivable or
payable account and left unreconciled, with a message on the payment order. A line
whose linked invoice is not posted or has a different number of installments, or
whose installment is already fully paid, is booked on the account of that invoice
and left unreconciled, with the same message.
