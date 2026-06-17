"""
Generate synthetic trade finance PDFs for the three test cases.

Case 001 — clean presentation, all documents compliant → HONOUR
Case 002 — invoice amount exceeds L/C value → major discrepancy
Case 003 — sanctions hit on named party → processing freeze

Run from the project root:
    python scripts/generate_sample_docs.py
"""

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

BASE = Path(__file__).resolve().parent.parent / "data" / "sample_documents"
STYLES = getSampleStyleSheet()


def _doc(path: Path) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        str(path),
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
    )


def _h1(text: str) -> Paragraph:
    return Paragraph(text, ParagraphStyle("h1", parent=STYLES["Heading1"], spaceAfter=6))


def _h2(text: str) -> Paragraph:
    return Paragraph(text, ParagraphStyle("h2", parent=STYLES["Heading2"], spaceAfter=4))


def _p(text: str) -> Paragraph:
    return Paragraph(text, STYLES["Normal"])


def _table(data: list[list], col_widths=None) -> Table:
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING",    (0, 0), (-1, -1), 4),
    ]))
    return t


def _kv_table(pairs: list[tuple[str, str]]) -> Table:
    data = [[k, v] for k, v in pairs]
    t = Table(data, colWidths=[6 * cm, 11 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("GRID",      (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f9f9f9")]),
        ("VALIGN",    (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING",   (0, 0), (-1, -1), 4),
    ]))
    return t


# ── CASE 001 — CLEAN ─────────────────────────────────────────────────────────

def gen_001_letter_of_credit(out: Path) -> None:
    doc = _doc(out)
    story = [
        _h1("DOCUMENTARY LETTER OF CREDIT"),
        _p("IRREVOCABLE DOCUMENTARY CREDIT — UCP 600"),
        Spacer(1, 0.4 * cm),
        _kv_table([
            ("Credit Number:",           "LC-2024-001"),
            ("Date of Issue:",           "2024-10-01"),
            ("Date and Place of Expiry:","2024-12-31, Singapore"),
            ("Issuing Bank:",            "Global Trade Bank, Singapore"),
            ("Advising Bank:",           "EuroFinance Bank, Milan, Italy"),
            ("Applicant:",               "Guangzhou Trading Co. Ltd, 88 Tianhe Road, Guangzhou, China"),
            ("Beneficiary:",             "Mediterranean Exports Ltd, Via Roma 12, Milan, Italy"),
            ("Amount:",                  "USD 125,000.00"),
            ("Currency:",                "USD"),
            ("Latest Shipment Date:",    "2024-12-15"),
            ("Port of Loading:",         "Shanghai, China"),
            ("Port of Discharge:",       "Genoa, Italy"),
            ("Partial Shipments:",       "Prohibited"),
            ("Transhipment:",            "Prohibited"),
            ("Goods Description:",       "Cotton Fabric, 5,000 metres, CIF Genoa"),
            ("Presentation Period:",     "21 days after date of shipment"),
            ("ICC Rules:",               "UCP 600"),
        ]),
        Spacer(1, 0.4 * cm),
        _h2("Required Documents"),
        _p("1. Signed Commercial Invoice in triplicate<br/>"
           "2. Full set of Clean On-Board Ocean Bills of Lading<br/>"
           "3. Packing List<br/>"
           "4. Certificate of Origin issued by Chamber of Commerce<br/>"
           "5. Insurance Certificate covering All Risks for 110% of invoice value"),
        Spacer(1, 0.4 * cm),
        _p("This credit is subject to the Uniform Customs and Practice for Documentary "
           "Credits, 2007 Revision, International Chamber of Commerce Publication No. 600."),
    ]
    doc.build(story)
    print(f"  Written: {out}")


def gen_001_commercial_invoice(out: Path) -> None:
    doc = _doc(out)
    story = [
        _h1("COMMERCIAL INVOICE"),
        Spacer(1, 0.3 * cm),
        _kv_table([
            ("Invoice Number:",  "INV-2024-001"),
            ("Invoice Date:",    "2024-12-10"),
            ("Seller:",         "Mediterranean Exports Ltd, Via Roma 12, Milan, Italy"),
            ("Buyer:",          "Guangzhou Trading Co. Ltd, 88 Tianhe Road, Guangzhou, China"),
            ("Payment Terms:",  "Letter of Credit No. LC-2024-001"),
            ("Incoterms:",      "CIF Genoa"),
            ("Currency:",       "USD"),
        ]),
        Spacer(1, 0.4 * cm),
        _table(
            [
                ["Item", "Description",     "Qty",       "Unit Price (USD)", "Amount (USD)"],
                ["001",  "Cotton Fabric",   "5,000 m",   "25.00",            "125,000.00"],
            ],
            col_widths=[2*cm, 5*cm, 3*cm, 4*cm, 4*cm],
        ),
        Spacer(1, 0.4 * cm),
        _kv_table([
            ("Total Amount:", "USD 125,000.00"),
            ("In Words:",     "United States Dollars One Hundred Twenty-Five Thousand Only"),
        ]),
        Spacer(1, 0.6 * cm),
        _p("We hereby certify that this invoice is true and correct and that the goods "
           "were manufactured in Italy."),
    ]
    doc.build(story)
    print(f"  Written: {out}")


def gen_001_bill_of_lading(out: Path) -> None:
    doc = _doc(out)
    story = [
        _h1("BILL OF LADING"),
        _p("CLEAN ON BOARD OCEAN BILL OF LADING"),
        Spacer(1, 0.3 * cm),
        _kv_table([
            ("B/L Number:",        "BL-2024-001"),
            ("Date of Issue:",     "2024-12-12"),
            ("Shipper:",           "Mediterranean Exports Ltd, Via Roma 12, Milan, Italy"),
            ("Consignee:",         "TO ORDER OF GLOBAL TRADE BANK"),
            ("Notify Party:",      "Guangzhou Trading Co. Ltd, 88 Tianhe Road, Guangzhou, China"),
            ("Vessel Name:",       "MSC ALLEGRA"),
            ("Voyage Number:",     "VOY-2024-112"),
            ("Port of Loading:",   "Shanghai, China"),
            ("Port of Discharge:", "Genoa, Italy"),
            ("Goods Description:", "Cotton Fabric — 5,000 Metres"),
            ("Number of Packages:","50 Bales"),
            ("Gross Weight:",      "2,500 KG"),
            ("Freight:",           "PREPAID"),
        ]),
        Spacer(1, 0.4 * cm),
        _p("SHIPPED ON BOARD in apparent good order and condition."),
        Spacer(1, 0.3 * cm),
        _p("This Bill of Lading is issued subject to the terms and conditions on the "
           "reverse hereof, all of which are incorporated herein."),
    ]
    doc.build(story)
    print(f"  Written: {out}")


def gen_001_packing_list(out: Path) -> None:
    doc = _doc(out)
    story = [
        _h1("PACKING LIST"),
        Spacer(1, 0.3 * cm),
        _kv_table([
            ("Date:",             "2024-12-10"),
            ("Shipper:",         "Mediterranean Exports Ltd, Milan, Italy"),
            ("Consignee:",       "Guangzhou Trading Co. Ltd, Guangzhou, China"),
            ("Marks & Numbers:", "LC-2024-001 / GTC"),
        ]),
        Spacer(1, 0.4 * cm),
        _table(
            [
                ["Bale No.", "Description",  "Metres",  "Net Wt (KG)", "Gross Wt (KG)"],
                ["001–010",  "Cotton Fabric","1,000 m", "480",         "500"],
                ["011–020",  "Cotton Fabric","1,000 m", "480",         "500"],
                ["021–030",  "Cotton Fabric","1,000 m", "480",         "500"],
                ["031–040",  "Cotton Fabric","1,000 m", "480",         "500"],
                ["041–050",  "Cotton Fabric","1,000 m", "480",         "500"],
                ["TOTAL",    "",             "5,000 m", "2,400 KG",    "2,500 KG"],
            ],
            col_widths=[3*cm, 4.5*cm, 2.5*cm, 3.5*cm, 3.5*cm],
        ),
        Spacer(1, 0.4 * cm),
        _kv_table([
            ("Total Packages:",    "50 Bales"),
            ("Total Net Weight:",  "2,400 KG"),
            ("Total Gross Weight:","2,500 KG"),
        ]),
    ]
    doc.build(story)
    print(f"  Written: {out}")


def gen_001_certificate_of_origin(out: Path) -> None:
    doc = _doc(out)
    story = [
        _h1("CERTIFICATE OF ORIGIN"),
        Spacer(1, 0.3 * cm),
        _kv_table([
            ("Certificate No.:",      "CO-2024-001"),
            ("Date of Issue:",        "2024-12-10"),
            ("Exporter:",             "Mediterranean Exports Ltd, Via Roma 12, Milan, Italy"),
            ("Consignee:",            "Guangzhou Trading Co. Ltd, Guangzhou, China"),
            ("Country of Origin:",    "Italy"),
            ("Goods Description:",    "Cotton Fabric — 5,000 Metres"),
            ("Certifying Authority:", "Milan Chamber of Commerce"),
        ]),
        Spacer(1, 0.5 * cm),
        _p("The Milan Chamber of Commerce hereby certifies that the goods described "
           "above are of Italian origin."),
        Spacer(1, 0.3 * cm),
        _p("Authorised Signatory: __________________________"),
        _p("Stamp: [MILAN CHAMBER OF COMMERCE — OFFICIAL SEAL]"),
    ]
    doc.build(story)
    print(f"  Written: {out}")


# ── CASE 002 — INVOICE AMOUNT MISMATCH ───────────────────────────────────────

def gen_002_letter_of_credit(out: Path) -> None:
    doc = _doc(out)
    story = [
        _h1("DOCUMENTARY LETTER OF CREDIT"),
        _p("IRREVOCABLE DOCUMENTARY CREDIT — UCP 600"),
        Spacer(1, 0.4 * cm),
        _kv_table([
            ("Credit Number:",           "LC-2024-002"),
            ("Date of Issue:",           "2024-10-15"),
            ("Date and Place of Expiry:","2025-01-31, Hong Kong"),
            ("Issuing Bank:",            "Asia Pacific Bank, Hong Kong"),
            ("Advising Bank:",           "Trade Finance Bank, Jakarta, Indonesia"),
            ("Applicant:",               "Sunrise Electronics Ltd, Hong Kong"),
            ("Beneficiary:",             "PT Komponan Nusantara, Jakarta, Indonesia"),
            ("Amount:",                  "USD 98,500.00"),
            ("Currency:",                "USD"),
            ("Latest Shipment Date:",    "2025-01-15"),
            ("Port of Loading:",         "Tanjung Priok, Jakarta"),
            ("Port of Discharge:",       "Kwai Chung, Hong Kong"),
            ("Partial Shipments:",       "Prohibited"),
            ("Transhipment:",            "Prohibited"),
            ("Goods Description:",       "Electronic Components — PCBs, 500 units"),
            ("Presentation Period:",     "21 days after date of shipment"),
            ("ICC Rules:",               "UCP 600"),
        ]),
    ]
    doc.build(story)
    print(f"  Written: {out}")


def gen_002_commercial_invoice(out: Path) -> None:
    doc = _doc(out)
    story = [
        _h1("COMMERCIAL INVOICE"),
        Spacer(1, 0.3 * cm),
        _kv_table([
            ("Invoice Number:",  "INV-2024-002"),
            ("Invoice Date:",    "2025-01-10"),
            ("Seller:",         "PT Komponan Nusantara, Jakarta, Indonesia"),
            ("Buyer:",          "Sunrise Electronics Ltd, Hong Kong"),
            ("Payment Terms:",  "Letter of Credit No. LC-2024-002"),
            ("Incoterms:",      "FOB Jakarta"),
            ("Currency:",       "USD"),
        ]),
        Spacer(1, 0.4 * cm),
        _table(
            [
                ["Item", "Description",         "Qty",     "Unit Price (USD)", "Amount (USD)"],
                ["001",  "PCB Assembly Type A", "300 pcs", "164.00",           "49,200.00"],
                ["002",  "PCB Assembly Type B", "200 pcs", "250.00",           "50,000.00"],
            ],
            col_widths=[2*cm, 5*cm, 3*cm, 4*cm, 4*cm],
        ),
        Spacer(1, 0.4 * cm),
        _kv_table([
            ("Total Amount:", "USD 99,200.00"),
            ("In Words:",     "United States Dollars Ninety-Nine Thousand Two Hundred Only"),
        ]),
        Spacer(1, 0.3 * cm),
        _p("NOTE: Invoice total USD 99,200.00 exceeds L/C amount of USD 98,500.00 "
           "by USD 700.00 (approximately 0.71%)."),
    ]
    doc.build(story)
    print(f"  Written: {out}")


def gen_002_bill_of_lading(out: Path) -> None:
    doc = _doc(out)
    story = [
        _h1("BILL OF LADING"),
        Spacer(1, 0.3 * cm),
        _kv_table([
            ("B/L Number:",        "BL-2024-002"),
            ("Date of Issue:",     "2025-01-12"),
            ("Shipper:",           "PT Komponan Nusantara, Jakarta, Indonesia"),
            ("Consignee:",         "TO ORDER OF ASIA PACIFIC BANK"),
            ("Notify Party:",      "Sunrise Electronics Ltd, Hong Kong"),
            ("Vessel Name:",       "PACIFIC VOYAGER"),
            ("Voyage Number:",     "VOY-2025-005"),
            ("Port of Loading:",   "Tanjung Priok, Jakarta, Indonesia"),
            ("Port of Discharge:", "Kwai Chung, Hong Kong"),
            ("Goods Description:", "Electronic Components — 500 units PCB Assemblies"),
            ("Number of Packages:","10 Cartons"),
            ("Gross Weight:",      "350 KG"),
            ("Freight:",           "COLLECT"),
        ]),
        Spacer(1, 0.4 * cm),
        _p("SHIPPED ON BOARD in apparent good order and condition."),
    ]
    doc.build(story)
    print(f"  Written: {out}")


# ── CASE 003 — SANCTIONS HIT ─────────────────────────────────────────────────

def gen_003_letter_of_credit(out: Path) -> None:
    doc = _doc(out)
    story = [
        _h1("DOCUMENTARY LETTER OF CREDIT"),
        _p("IRREVOCABLE DOCUMENTARY CREDIT — UCP 600"),
        Spacer(1, 0.4 * cm),
        _kv_table([
            ("Credit Number:",           "LC-2024-003"),
            ("Date of Issue:",           "2024-11-01"),
            ("Date and Place of Expiry:","2025-02-28, Dubai"),
            ("Issuing Bank:",            "Emirates Commercial Bank, Dubai, UAE"),
            ("Advising Bank:",           "Caspian Trade Finance Bank, Baku, Azerbaijan"),
            ("Applicant:",               "Gulf Petroleum Trading LLC, Dubai, UAE"),
            ("Beneficiary:",             "Petro Caspian Exports, Baku, Azerbaijan"),
            ("Amount:",                  "USD 450,000.00"),
            ("Currency:",                "USD"),
            ("Latest Shipment Date:",    "2025-02-15"),
            ("Port of Loading:",         "Baku, Azerbaijan"),
            ("Port of Discharge:",       "Jebel Ali, UAE"),
            ("Partial Shipments:",       "Allowed"),
            ("Transhipment:",            "Prohibited"),
            ("Goods Description:",       "Petrochemical Products — 500 MT Methanol"),
            ("Presentation Period:",     "21 days after date of shipment"),
            ("ICC Rules:",               "UCP 600"),
        ]),
    ]
    doc.build(story)
    print(f"  Written: {out}")


def gen_003_commercial_invoice(out: Path) -> None:
    doc = _doc(out)
    story = [
        _h1("COMMERCIAL INVOICE"),
        Spacer(1, 0.3 * cm),
        _kv_table([
            ("Invoice Number:",  "INV-2024-003"),
            ("Invoice Date:",    "2025-02-05"),
            ("Seller:",         "Petro Caspian Exports, Baku, Azerbaijan"),
            ("Buyer:",          "Gulf Petroleum Trading LLC, Dubai, UAE"),
            ("Payment Terms:",  "Letter of Credit No. LC-2024-003"),
            ("Incoterms:",      "CFR Jebel Ali"),
            ("Currency:",       "USD"),
            ("Notify Party:",   "Iran National Petrochemical Co., Tehran, Iran"),
        ]),
        Spacer(1, 0.4 * cm),
        _table(
            [
                ["Item", "Description", "Qty",   "Unit Price (USD)", "Amount (USD)"],
                ["001",  "Methanol",    "500 MT", "900.00",           "450,000.00"],
            ],
            col_widths=[2*cm, 5*cm, 3*cm, 4*cm, 4*cm],
        ),
        Spacer(1, 0.4 * cm),
        _kv_table([
            ("Total Amount:", "USD 450,000.00"),
            ("In Words:",     "United States Dollars Four Hundred Fifty Thousand Only"),
        ]),
        Spacer(1, 0.3 * cm),
        _p("Shipping arranged via: Sadra Shipping Lines, Bandar Abbas, Iran — "
           "Vessel: MV IRAN SHAHED — Flag: Islamic Republic of Iran"),
    ]
    doc.build(story)
    print(f"  Written: {out}")


def gen_003_bill_of_lading(out: Path) -> None:
    doc = _doc(out)
    story = [
        _h1("BILL OF LADING"),
        Spacer(1, 0.3 * cm),
        _kv_table([
            ("B/L Number:",        "BL-2024-003"),
            ("Date of Issue:",     "2025-02-08"),
            ("Shipper:",           "Petro Caspian Exports, Baku, Azerbaijan"),
            ("Consignee:",         "TO ORDER OF EMIRATES COMMERCIAL BANK"),
            ("Notify Party:",      "Gulf Petroleum Trading LLC, Dubai, UAE"),
            ("Vessel Name:",       "MV IRAN SHAHED"),
            ("Vessel Flag:",       "Islamic Republic of Iran"),
            ("Voyage Number:",     "VOY-2025-018"),
            ("Port of Loading:",   "Baku, Azerbaijan"),
            ("Port of Discharge:", "Jebel Ali, UAE"),
            ("Goods Description:", "Methanol — 500 Metric Tonnes"),
            ("Number of Packages:","Bulk Liquid"),
            ("Gross Weight:",      "500,000 KG"),
            ("Freight:",           "PREPAID"),
            ("Shipping Company:",  "Sadra Shipping Lines, Bandar Abbas, Iran"),
        ]),
        Spacer(1, 0.4 * cm),
        _p("SHIPPED ON BOARD in apparent good order and condition."),
    ]
    doc.build(story)
    print(f"  Written: {out}")


# ── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cases = {
        "case_001_clean": [
            ("letter_of_credit.pdf",     gen_001_letter_of_credit),
            ("commercial_invoice.pdf",   gen_001_commercial_invoice),
            ("bill_of_lading.pdf",       gen_001_bill_of_lading),
            ("packing_list.pdf",         gen_001_packing_list),
            ("certificate_of_origin.pdf",gen_001_certificate_of_origin),
        ],
        "case_002_invoice_mismatch": [
            ("letter_of_credit.pdf",   gen_002_letter_of_credit),
            ("commercial_invoice.pdf", gen_002_commercial_invoice),
            ("bill_of_lading.pdf",     gen_002_bill_of_lading),
        ],
        "case_003_sanctions_hit": [
            ("letter_of_credit.pdf",   gen_003_letter_of_credit),
            ("commercial_invoice.pdf", gen_003_commercial_invoice),
            ("bill_of_lading.pdf",     gen_003_bill_of_lading),
        ],
    }

    for case_name, docs in cases.items():
        out_dir = BASE / case_name
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n{case_name}/")
        for filename, generator in docs:
            generator(out_dir / filename)

    print("\nDone — all sample documents generated.")
