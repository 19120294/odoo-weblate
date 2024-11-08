# models/estate_property_offer.py
from odoo import models, fields, api


class EstatePropertyOffer(models.Model):
    _inherit = "estate.property.offer"

    user_accept = fields.Many2one(
        "res.users",
        string="User Accept",
        readonly=True,
    )
    user_reject = fields.Many2one(
        "res.users",
        string="User Reject",
        readonly=True,
    )

    def action_accept(self):
        super(EstatePropertyOffer, self).action_accept()
        self.user_accept = self.env.user
        self.send_offer_mail

    def action_reject(self):
        super(EstatePropertyOffer, self).action_reject()
        self.user_reject = self.env.user
        

    def send_offer_mail(self):
            for record in self:
                if record.state == 'sold':
                    mail_template = self.env.ref('estate_send_mail.email_template_offer_accepted')
                    mail_template.sudo().send_mail(record.id, force_send=True)