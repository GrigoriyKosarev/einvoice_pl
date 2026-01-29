# FA(2) vs FA(3) Schema Comparison

## ⚠️ IMPORTANT: FA(3) Not Yet Available in KSeF

**AS OF JANUARY 2026**: FA(3) schema is **NOT yet deployed** to KSeF system (test or production).

**Current status:**
- ✅ **FA(2)**: Fully working and accepted by KSeF
- ⚠️ **FA(3)**: Schema exists in documentation but KSeF rejects it with error:
  ```
  Could not find schema information for the element 'http://crd.gov.pl/wzor/2025/06/25/13775/:Faktura'
  ```

**Recommendation**: **Use FA(2) only** until KSeF officially announces FA(3) support (expected around September 1, 2025).

Our implementation is future-ready and will work automatically once KSeF activates FA(3).

---

## Overview

FA(2) and FA(3) are **SEPARATE** invoice schemas for the Polish KSeF (Krajowy System e-Faktur) system. They have different XML namespaces, different WariantFormularza values, and different supported features.

## Critical Differences

| Feature | FA(2) | FA(3) |
|---------|-------|-------|
| **KSeF Deployment Status** | ✅ Active | ⚠️ Not deployed yet |
| **Namespace** | `http://crd.gov.pl/wzor/2023/06/29/12648/` | `http://crd.gov.pl/wzor/2025/06/25/13775/` |
| **WariantFormularza** | `2` | `3` |
| **kodSystemowy** | `FA (2)` | `FA (3)` |
| **Schema Version** | `1-0E` | `1-0E` |
| **Valid Date Range** | Until Aug 31, 2025 | Sept 1, 2025 - Jan 1, 2050 |
| **DodatkowyOpis Support** | ❌ NO | ❌ NO |
| **Customer Product Info** | ❌ NOT supported | ❌ NOT supported |

## Schema URLs

### FA(2) Schema
- **Schema XSD**: Previous implementation (docs/FA3/schemat.xsd was actually FA(2))
- **Namespace**: `http://crd.gov.pl/wzor/2023/06/29/12648/`

### FA(3) Schema
- **Wyróżnik**: http://crd.gov.pl/wzor/2025/06/25/13775/wyroznik.xml
- **Schema XSD**: http://crd.gov.pl/wzor/2025/06/25/13775/schemat.xsd
- **Style XSL**: http://crd.gov.pl/wzor/2025/06/25/13775/styl.xsl
- **Namespace**: `http://crd.gov.pl/wzor/2025/06/25/13775/`

## ❌ DodatkowyOpis (Customer Product Information) - NOT SUPPORTED

**IMPORTANT DISCOVERY**: The `DodatkowyOpis` element is **NOT supported** in either FA(2) or FA(3)!

**KSeF validation error confirms this:**
```
The element 'FaWiersz' has invalid child element 'DodatkowyOpis'.
List of possible elements expected: 'P_12_XII, P_12_Zal_15, KwotaAkcyzy, GTU, Procedura, KursWaluty, StanPrzed'
```

`DodatkowyOpis` is **not in the list** of valid FaWiersz child elements.

### Alternative Solutions for Customer Product Info

Since `DodatkowyOpis` cannot be used, consider these alternatives:

1. **P_7 (Product Description)**: Include customer-specific product name/code in the description field
   ```xml
   <P_7>[YOUR-SKU] Product Name | Customer: CUST-SKU Customer Product Name</P_7>
   ```

2. **Indeks (Product Code)**: Use for internal product code (not customer-specific)
   ```xml
   <Indeks>YOUR-INTERNAL-SKU</Indeks>
   ```

3. **GTIN (Barcode)**: Use standard product barcode
   ```xml
   <GTIN>1234567890123</GTIN>
   ```

**Conclusion**: Customer-specific product information cannot be structured separately in KSeF invoices. It must be included in the standard P_7 description field if needed.

## Migration Timeline

### Until August 31, 2025
- **Use FA(2)** for all invoices
- Standard fields: P_7, Indeks, GTIN available

### From September 1, 2025
- **Switch to FA(3)** (when KSeF deploys it)
- Same standard fields available as FA(2)
- Monitor KSeF announcements for FA(3) deployment

## Implementation in Code

### XML Generator (`ksef_client/xml_generator.py`)

The `generate_fa_vat_xml()` function now supports both formats:

```python
# FA(2) - Current schema (until Aug 31, 2025)
xml = generate_fa_vat_xml(invoice_data, format_version='FA2')

# FA(3) - New schema (from Sept 1, 2025)
xml = generate_fa_vat_xml(invoice_data, format_version='FA3')
```

**Automatic handling**:
- When `format_version='FA2'`: Uses FA(2) namespace, generates DodatkowyOpis if provided
- When `format_version='FA3'`: Uses FA(3) namespace, skips DodatkowyOpis (even if provided)

### Configuration Model (`models/ksef_config.py`)

The `fa_version` field allows selecting the format:

- **FA2**: Current schema (valid until Aug 31, 2025)
- **FA3**: New schema (valid from Sept 1, 2025)

## Testing Recommendations

### Current Testing (FA(2))
1. Test invoices with FA(2) format
2. Verify standard fields: P_7, Indeks, GTIN
3. Test credit notes with FA(2)
4. Verify all required fields are correctly populated

### After FA(3) Deployment (Sept 1, 2025)
1. Monitor KSeF announcements for FA(3) availability
2. Test in test environment first
3. Verify invoices are accepted with new namespace
4. Verify same standard fields work as in FA(2)

## Common Issues

### Issue 0: FA(3) schema not found in KSeF
**Symptom**: KSeF rejects FA(3) invoice with error:
```
Could not find schema information for the element 'http://crd.gov.pl/wzor/2025/06/25/13775/:Faktura'
```

**Cause**: FA(3) schema has not been deployed to KSeF system yet, even though it exists in official documentation

**Solution**:
- **Use FA(2)** until KSeF officially deploys FA(3) support
- Monitor KSeF announcements for FA(3) availability (expected around September 1, 2025)
- The code implementation is correct and will work automatically once KSeF activates FA(3)

### Issue 1: DodatkowyOpis not supported
**Symptom**: KSeF rejects invoice with error:
```
The element 'FaWiersz' has invalid child element 'DodatkowyOpis'.
List of possible elements expected: 'P_12_XII, P_12_Zal_15, KwotaAkcyzy, GTU, Procedura, KursWaluty, StanPrzed'
```

**Cause**: DodatkowyOpis element is not supported in FA(2) or FA(3) schemas

**Solution**:
- Remove DodatkowyOpis from invoice XML
- Use P_7 (product description) field to include customer-specific information if needed
- Use standard fields: Indeks (internal SKU), GTIN (barcode)

### Issue 2: Wrong namespace for FA(3)
**Symptom**: KSeF rejects invoice with namespace error

**Cause**: Using FA(2) namespace (`2023/06/29/12648`) for FA(3) invoice

**Solution**: Ensure `format_version='FA3'` is set correctly in configuration

### Issue 3: Wrong WariantFormularza value
**Symptom**: KSeF rejects with "Enumeration constraint failed" for WariantFormularza

**Cause**: Using WariantFormularza=2 for FA(3) or WariantFormularza=3 for FA(2)

**Solution**:
- FA(2) MUST use WariantFormularza=2
- FA(3) MUST use WariantFormularza=3

## References

- Official FA(3) Schema: http://crd.gov.pl/wzor/2025/06/25/13775/schemat.xsd
- Schema valid date range: September 1, 2025 - January 1, 2050
