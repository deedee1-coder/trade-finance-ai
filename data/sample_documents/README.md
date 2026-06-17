# Sample Trade Bundle Cases

These bundles are small test cases for the ITFDS pipeline. Each folder has a
`manifest.yaml`, trade PDFs, and usually a `case_metadata.json` file with the
expected scenario.

Running a full demo calls Agent B, which can use the OpenAI API. Use only the
cases you need when testing with real credits.

| Case | Scenario | Expected behavior | Format notes |
|---|---|---|---|
| case_001_clean | Clean document set | Baseline clean/pass case | Existing sample PDFs |
| case_002_invoice_mismatch | Invoice amount mismatch | Refuse or manual review | Existing sample PDFs |
| case_003_sanctions_hit | Sanctions-risk party/vessel | Hold or manual review | Existing sample PDFs |
| case_004_missing_packing_list | Required packing list is missing | Missing-document finding | Generated colored PDFs, intentionally no packing list |
| case_005_late_shipment | B/L shipment date is after latest shipment date | Major discrepancy/refuse | Generated colored PDFs |
| case_006_late_presentation | Presented after the 21-day rule | Late-presentation finding | Generated colored PDFs |
| case_007_currency_mismatch | L/C and invoice currencies differ | Currency mismatch/refuse | Generated colored PDFs |
| case_008_partial_shipment_violation | Partial shipment despite prohibition | Partial-shipment finding | Generated colored PDFs |
| case_009_scanned_lc_ocr_needed | Image-only L/C PDF | Should require OCR fallback | Scanned/image-style L/C, readable supporting PDFs |
| case_010_expired_lc | Presentation after L/C expiry date | Expired-credit finding/refuse | Generated colored PDFs |

Example:

```powershell
python scripts\run_demo.py case_005_late_shipment
```

OCR note: `case_009_scanned_lc_ocr_needed` is included to prove whether OCR is
really working. At the moment, the project extracts text with `pdfplumber`, but
does not run Tesseract OCR fallback yet.
