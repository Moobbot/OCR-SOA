# Rule Analysis & Mapping

This document transforms the raw rules from `some_rule.txt`, `page_type.txt`, `rule_2.txt`, and **`rule_3.txt`** into structured tables for verification.

## 1. Page Identification Rules

| Page Type       | Priority | Identification Logic                                                                                                      |
| :-------------- | :------- | :------------------------------------------------------------------------------------------------------------------------ |
| **Positions**   | 100      | **Any of:**<br>1. Contains "Detailed positions" AND "Last purchase"<br>2. Contains "Liquidity - Accounts" AND "Valued in" |
| **Transaction** | 80       | Contains "Transaction list" AND "Valued in"                                                                               |
| **Others**      | 0        | Fallback (All remaining cases)                                                                                            |

**Transaction Sub-classification (Post-process)**:
If Page Type is **Transaction**, check for Sub-type:

- **FXTX** (Priority 90):
  - Contains "FX FORWARD"
  - Contains "FX SPOT"
  - Contains "SPOT" AND does NOT contain "SALE"
- **Trade information** (Priority 10): Default if not FXTX.

---

## 2. Trade Information

**Page Type**: Transaction (Sub-type: Trade information)

**Columns**:

| Index | Column Name                 | Format |
| :---- | :-------------------------- | :----- |
| 1     | Client name                 | Text   |
| 2     | Name/ Security              | Text   |
| 3     | Securities ID               | Text   |
| 4     | Transaction type            | Text   |
| 5     | Trade date                  | Date   |
| 6     | Settlement date             | Number |
| 7     | Quantity                    | Text   |
| 8     | Foreign Unit Price          | Number |
| 9     | Foreign Gross consideration | Text   |
| 10    | Foreign Transaction Fee     | Number |
| 11    | Accrued interest            | Text   |
| 12    | Foreign Net consideration   | Number |
| 13    | Currency                    | Text   |
| 14    | Net consideration           | Number |
| 15    | Account no.                 | Text   |
| 16    | Commission fee (Base)       | Number |

**Extraction Rules & Constraints**:

| Field                           | Source / Logic                                                                            | Constraints / Description                                     |
| :------------------------------ | :---------------------------------------------------------------------------------------- | :------------------------------------------------------------ |
| **Client name**                 | Page text: Text between portfolio # and 'Statement of assets'                             |                                                               |
| **Name/ Security**              | **Custody account**: Clean description, remove leading numbers.                           | Should be named clearly                                       |
| **Securities ID**               | **Custody account**: Alphanumeric after 'ISIN'                                            | ISIN (12 chars)<br>Constraint: Max 15 chars, No special chars |
| **Transaction type**            | **Booking text**: Classifier `transaction_type_rules`                                     |                                                               |
| **Trade date**                  | **Trade date**: 1st date found                                                            | Keywords: `trade date`, `traded on`, `booking date`           |
| **Settlement date**             | **Trade date**: 2nd date found (or last)                                                  | Keywords: `Value date`, `Settlement due on`...                |
| **Quantity**                    | **Transaction Tax** (1st value) OR **Name/ Security** (leading num)                       | Constraint: Units of securities, Quantity >= 0                |
| **Foreign Unit Price**          | **Buy**: Cost/Purchase price (skip 1st token)<br>**Sell**: Transaction price (last token) | Constraint: Max 12 decimals                                   |
| **Foreign Gross consideration** | **Transaction value**: Sale Spot (1st val), Others (last val)                             | Rule: Absolute value                                          |
| **Foreign Transaction Fee**     | Keywords match                                                                            | Maximum 2 decimals                                            |
| **Accrued interest**            | **Transaction value**: Sale Spot (2nd value)                                              |                                                               |
| **Currency**                    | Trans Tax OR Cost/Purch price OR Trans value OR 'Valued in [CCY]'                         | Map to `SYSTEM/CURRENCIES`                                    |
| **Account no.**                 | **Custody account**: Regex `\d{3}-\d{6}.[A-Z0-9]+`                                        |                                                               |

**Transaction Type Classification Rules**:

(Same as before - consolidated list)

---

## 3. FX & TF

**Page Type**: Transaction (Sub-type: FXTX)

**Columns**: Columns 1-11 same as JSON...

**Extraction Rules & Constraints**:

| Field                 | Source / Logic                                        | Constraints                |
| :-------------------- | :---------------------------------------------------- | :------------------------- |
| **Transaction type**  | **Booking text**: Classifier `transaction_type_rules` |                            |
| **Currency Buy/Sell** |                                                       | Map to `SYSTEM/CURRENCIES` |
| **Account no. Buy**   | Match 'Bought [Currency]'                             | Identifier from SOA data   |
| **Account no. Sell**  | Match 'Sold [Currency]'                               | Identifier from SOA data   |

---

## 4. Others

**Page Type**: Others (Fallback)

**Extraction Rules & Constraints**:
(Similar generic constraints as Trade Info)

---

## 5. Positions

**Page Type**: Positions

**Columns**: Columns 1-12...

**Extraction Rules & Constraints**:

| Field                 | Source / Logic                                | Description / Constraints          |
| :-------------------- | :-------------------------------------------- | :--------------------------------- |
| **Portfolio No.**     | Regex `\d{3}-\d{6}-\d{2}`                     |                                    |
| **Type**              | **Section Header**                            | e.g., 'Bonds', 'Equities'          |
| **Currency**          | **By investment category**                    | Map to `SYSTEM/CURRENCIES`         |
| **Quantity/ Amount**  | **By investment category** OR **Description** | Units of securities, Quantity >= 0 |
| **ISIN**              | **Description**: After 'ISIN:'                | Max 15 chars, No special chars     |
| **Secuitity name**    | **Description**: Cleaned text                 | Should be named clearly            |
| **Cost/Market price** | Cols `Cost price` / `Market price`            | Handle percentages                 |
| **Valuation date**    | 'Market price on' or 'Valued in'              |                                    |
