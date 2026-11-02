from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter

from .services import Reconciliation

MONEY_FORMAT = "#,##0.00"
HEADERS = ("Sana", "Hujjat", "Turi", "Tavsif", "Debet", "Kredit", "Qoldiq")
WIDTHS = (12, 12, 20, 40, 14, 14, 14)


def reconciliation_xlsx(rec: Reconciliation) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Akt-sverka"
    bold = Font(bold=True)
    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.append(["O'zaro hisob-kitoblarni solishtirish dalolatnomasi"])
    ws["A1"].font = Font(bold=True, size=13)
    ws.append([f"Mijoz: {rec.customer.name}"])
    ws.append(
        [f"Davr: {rec.date_from:%d.%m.%Y} — {rec.date_to:%d.%m.%Y}", f"Valyuta: {rec.currency}"]
    )
    ws.append([])

    ws.append(HEADERS)
    header_row = ws.max_row
    for cell in ws[header_row]:
        cell.font = bold
        cell.border = border
        cell.alignment = Alignment(horizontal="center")

    ws.append(["", "", "", "Boshlang'ich qoldiq", None, None, rec.opening_balance])
    for row in rec.rows:
        ws.append(
            [
                row.date,
                row.reference,
                row.type_display,
                row.description,
                row.debit or None,
                row.credit or None,
                row.balance,
            ]
        )
    ws.append(["", "", "", "Davr bo'yicha jami", rec.debit_total, rec.credit_total, None])
    ws.append(["", "", "", "Yakuniy qoldiq", None, None, rec.closing_balance])

    for r in range(header_row + 1, ws.max_row + 1):
        ws.cell(r, 1).number_format = "DD.MM.YYYY"
        for c in range(1, len(HEADERS) + 1):
            ws.cell(r, c).border = border
        for c in (5, 6, 7):
            ws.cell(r, c).number_format = MONEY_FORMAT
    for r in (header_row + 1, ws.max_row - 1, ws.max_row):
        for cell in ws[r]:
            cell.font = bold

    for i, width in enumerate(WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
