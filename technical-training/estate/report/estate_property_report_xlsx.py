from odoo import http
from odoo.http import request
import io
import xlsxwriter
from datetime import datetime
from odoo import models
from odoo.exceptions import UserError


class EstatePropertyReportXlsx(models.AbstractModel):

    _name = "estate.property_report_xlsx"
    _inherit = "report.report_xlsx.abstract"

    def create_xlsx_report(self, data):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        buyer_id = data.get('buyer_id')  # A specific buyer ID, or None if all buyers
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        worksheet = workbook.add_worksheet('Buyer Offer Report')
        title_format = workbook.add_format({'bold': True, 'align': 'center', 'font_size': 12, 'border': 0})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'border': 1, 'bg_color': '#3a90d6', 'font_color': 'white'})
        date_format = workbook.add_format({'align': 'left', 'num_format': 'yyyy-mm-dd'})
        number_format = workbook.add_format({'align': 'right', 'num_format': '#,##0.00'})

        # Set title and date range
        worksheet.merge_range('A3:I3', 'Buyer Offer Report', title_format)
        worksheet.write('C5', 'Date From', title_format)
        worksheet.write('D5', start_date.strftime('%d/%m/%Y'), date_format)
        worksheet.write('F5', 'Date To', title_format)
        worksheet.write('G5', end_date.strftime('%d/%m/%Y'), date_format)

        # Set column widths
        worksheet.set_column('A:A', 20)  # Buyer name
        worksheet.set_column('B:B', 25)  # Email
        worksheet.set_column('C:G', 16)  # Other columns
        worksheet.set_column('H:I', 20)  # Max/Min Price Offer

        # Headers
        headers = [
            'Buyer', 'Email', 'Property Accepted', 'Property Sold',
            'Property Cancel', 'Offer Accepted', 'Offer Rejected',
            'Max Offer Price', 'Min Offer Price'
        ]
        for col, header in enumerate(headers):
            worksheet.write(7, col, header, header_format)

        query = """
            SELECT
                rp.name AS buyer_name,
                rp.email AS buyer_email,
                (SELECT COUNT(*) FROM estate_property ep_sub WHERE ep_sub.buyer_id = rp.id AND ep_sub.state = 'offer_accepted' AND ep_sub.date_availability BETWEEN %s AND %s) AS property_accepted,
                (SELECT COUNT(*) FROM estate_property ep_sub WHERE ep_sub.buyer_id = rp.id AND ep_sub.state = 'sold' AND ep_sub.date_availability BETWEEN %s AND %s) AS property_sold,
                (SELECT COUNT(*) FROM estate_property ep_sub WHERE ep_sub.buyer_id = rp.id AND ep_sub.state = 'canceled' AND ep_sub.date_availability BETWEEN %s AND %s) AS property_canceled,
                (SELECT COUNT(*) FROM estate_property_offer eo_sub WHERE eo_sub.property_id IN (SELECT id FROM estate_property WHERE buyer_id = rp.id AND date_availability BETWEEN %s AND %s) AND eo_sub.status = 'accepted') AS offer_accepted,
                (SELECT COUNT(*) FROM estate_property_offer eo_sub WHERE eo_sub.property_id IN (SELECT id FROM estate_property WHERE buyer_id = rp.id AND date_availability BETWEEN %s AND %s) AND eo_sub.status = 'rejected') AS offer_rejected,
                MAX(eo.price) AS max_price_offer,
                MIN(eo.price) AS min_price_offer
            FROM
                res_partner rp
            LEFT JOIN
                estate_property ep ON ep.buyer_id = rp.id
            LEFT JOIN
                estate_property_offer eo ON eo.property_id = ep.id
            WHERE
                ep.date_availability BETWEEN %s AND %s
                {buyer_filter}
            GROUP BY
                rp.id
        """

        # Add filter for multiple buyer_ids if provided
        buyer_filter = ""
        params = [start_date, end_date, start_date, end_date, start_date, end_date, start_date, end_date, start_date, end_date, start_date, end_date]
        if buyer_id:
            # Prepare a placeholder for each buyer_id in the IN clause
            buyer_filter = "AND rp.id IN ({})".format(','.join(['%s'] * len(buyer_id)))
            params.extend(buyer_id)

        # Execute query
        self.env.cr.execute(query.format(buyer_filter=buyer_filter), tuple(params))
        results = self.env.cr.fetchall()

        row = 8
        for report in results:
            worksheet.write(row, 0, report[0])  # Buyer Name
            worksheet.write(row, 1, report[1])  # Buyer Email
            worksheet.write(row, 2, report[2], number_format)  # Properties Accepted
            worksheet.write(row, 3, report[3], number_format)  # Properties Sold
            worksheet.write(row, 4, report[4], number_format)  # Properties Canceled
            worksheet.write(row, 5, report[5], number_format)  # Offers Accepted
            worksheet.write(row, 6, report[6], number_format)  # Offers Rejected
            worksheet.write(row, 7, report[7], number_format)  # Max Offer Price
            worksheet.write(row, 8, report[8], number_format)  # Min Offer Price
            row += 1
        workbook.close()
        output.seek(0)

        return output.getvalue()