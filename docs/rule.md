# Extraction Rules Analysis

## Section 1: Trade information

### Columns
| Index | Name | Format |
| --- | --- | --- |
| 1 | Client name | Text |
| 2 | Name/ Security | Text |
| 3 | Securities ID | Text |
| 4 | Transaction type | Text |
| 5 | Trade date | Date |
| 6 | Settlement date | Number |
| 7 | Quantity | Text |
| 8 | Foreign Unit Price | Number |
| 9 | Foreign Gross consideration | Text |
| 10 | Foreign Transaction Fee | Number |
| 11 | Accrued interest | Text |
| 12 | Foreign Net consideration | Number |
| 13 | Currency | Text |
| 14 | Net consideration | Number |
| 15 | Account no. | Text |
| 16 | Commission fee (Base) | Number |

### Extraction Rules
| Field | Source | Logic/Details | Constraints |
| --- | --- | --- | --- |
| Client name | Page text | Logic: Text between portfolio number and 'Statement of assets' |  |
| Name/ Security | Custody account | Logic: Cleaned description from 'Custody account' column. Remove leading quantities. | Should be named clearly |
| Securities ID | Custody account | Logic: Alphanumeric code following 'ISIN' token<br>Desc: ISIN (12 characters) | Should be ISIN<br>12 characters<br>Don't include special characters |
| Transaction type | Booking text | Classifier: transaction_type_rules |  |
| Trade date | Trade date | Logic: First date found in column<br>Keywords: trade date, traded on, booking date |  |
| Settlement date | Trade date | Logic: Second date found (or last date if multiple)<br>Keywords: Value date, Settlement due on, Settlement date, payment date, Receipt date |  |
| Quantity | Transaction Tax (first value), Name/ Security (leading number) |  | Units of securities<br>Quantity >= 0 |
| Foreign Unit Price | Buy: Cost/Purchase price (skip first token)<br>Sell: Transaction price (last token) |  | Maximum 12 decimals |
| Foreign Gross consideration | Transaction value | Logic: Sale Spot: First value; Others: Last value<br>Desc: Absolute value |  |
| Foreign Transaction Fee |  | Keywords: Commision, Exce commission, research commission, Local fee, local tax, stamp duty | Maximum 2 decimals |
| Accrued interest | Transaction value | Logic: Sale Spot: Second value |  |
| Currency | Transaction Tax, Cost/Purchase price, Transaction value, Valued in [CCY] |  | Please fill in the Currency in SYSTEM/CURRENCIES |
| Account no. | Custody account | Regex: `\d{3}-\d{6}.[A-Z0-9]+` |  |

## Section 2: FX & TF

### Columns
| Index | Name | Format |
| --- | --- | --- |
| 1 | Client name | Text |
| 2 | Transaction type | Text |
| 3 | Trade date | Date |
| 4 | Settlement date | Number |
| 5 | Rate | Number |
| 6 | Currency Buy | Text |
| 7 | Amount Buy | Number |
| 8 | Currency Sell | Text |
| 9 | Amount Sell | Number |
| 10 | Account no. Buy | Text |
| 11 | Account no. Sell | Text |

### Extraction Rules
| Field | Source | Logic/Details | Constraints |
| --- | --- | --- | --- |
| Transaction type |  | Classifier: transaction_type_rules |  |
| Currency Buy |  |  | Please fill in the Currency in SYSTEM/CURRENCIES |
| Currency Sell |  |  | Please fill in the Currency in SYSTEM/CURRENCIES |
| Account no. Buy |  | Desc: Identifier from SOA data. Match 'Bought [Currency]' with this field. |  |
| Account no. Sell |  | Desc: Identifier from SOA data. Match 'Sold [Currency]' with this field. |  |

## Section 3: Others

### Columns
| Index | Name | Format |
| --- | --- | --- |
| 1 | Client name | Text |
| 2 | Description | Text |
| 3 | Securities ID/ Ref-No. | Text |
| 4 | Transaction type | Date |
| 5 | Trade date | Text |
| 6 | Settlement date | Number |
| 7 | Currency | Text |
| 8 | Quantity | Text |
| 9 | Foreign Unit Price/ Interest rate | Number |
| 10 | Foreign Gross Amount/Interest | Text |
| 11 | Tax rate (%) | Text |
| 12 | Tax amount | Number |
| 13 | Foreign Net Amount | Number |
| 14 | Payment mode | Text |
| 15 | Account no. | Text |
| 16 | Exrate to GST | Number |
| 17 | Amount (SGD) | Number |

### Extraction Rules
| Field | Source | Logic/Details | Constraints |
| --- | --- | --- | --- |
| Securities ID/ Ref-No. |  |  | Should be ISIN<br>12 characters<br>Don't include special characters |
| Currency |  |  | Please fill in the Currency in SYSTEM/CURRENCIES |
| Quantity |  |  | Units of securities<br>Quantity >= 0 |
| Foreign Unit Price/ Interest rate |  |  | Maximum 12 decimals |

## Section 4: Positions

### Columns
| Index | Name | Format |
| --- | --- | --- |
| 1 | Portfolio No. | Text |
| 2 | Type | Text |
| 3 | Account No | Text |
| 4 | Currency | Number |
| 5 | Quantity/ Amount | Text |
| 6 | ISIN | Number |
| 7 | Secuitity name | Text |
| 8 | Cost price | Number |
| 9 | Market price | Number |
| 10 | Market value | Number |
| 11 | Accrued interest | Number |
| 12 | Valuation date | Date |

### Extraction Rules
| Field | Source | Logic/Details | Constraints |
| --- | --- | --- | --- |
| Portfolio No. |  | Regex: `\d{3}-\d{6}-\d{2}` |  |
| Type | Section Header | Desc: Extract from section headers (e.g. 'Bonds', 'Equities') |  |
| Account No | Description | Regex: `\d{3}-\d{6}\.[A-Z0-9]+` |  |
| Currency | Currency, SGD, USD, CHF, By investment category |  | Please fill in the Currency in SYSTEM/CURRENCIES |
| Quantity/ Amount | Quantity, Amount, Nominal, By investment category, Description |  | Units of securities<br>Quantity >= 0 |
| ISIN | Description | Desc: Extract from 'instrument ID', 12 chars after 'ISIN:' | Should be ISIN<br>12 characters<br>Don't include special characters |
| Secuitity name | Description, UBS, Serial no. | Logic: Cleaned description removing noise | Should be named clearly |
| Cost price | Cost price | Logic: Handle percentages |  |
| Market price | Price, %, Interest rate, Market price | Logic: Handle percentages |  |
| Market value | Value, Valued in SGD | Desc: Extract from column 'Market value' |  |
| Accrued interest |  | Desc: Extract from column 'Accrued interest' |  |
| Valuation date |  | Desc: Extract from 'Market price on' or 'Valued in' |  |

## Transaction Type Rules
| Name | Priority | Match Any | Output |
| --- | --- | --- | --- |
| UBS Call Deposit (Other) | 110 | UBS Call Deposit | Other |
| FX Forward | 100 | FX FORWARD | FX Forward |
| FX Spot (explicit) | 95 | FX SPOT | FX Spot |
| FX Spot (implicit) | 90 | SPOT | FX Spot |
| Sell | 70 | SOLD FOR YOU AS AGENT, BOUGHT FROM YOU AS PRINCIPAL, FRAMEWORK REDEMPTION, REDEMPTION, YOUR SALE, SEC. DELIVERY AGAINST PAYMENT, SALE SPOT, SALE, SELL | Sell |
| Buy | 60 | SOLD TO YOU AS PRINCIPAL, BOUGHT FOR YOU AS AGENT, NEW ISSUE PURCHASE, YOUR PURCHASE, SEC. RECEIPT AGAINST PAYMENT, PURCHASE, BUY | Buy |
| UBS Call Deposit | 40 | REDUCTION, REPAYMENT, INTEREST CAP. | UBS Call Deposit |
| Increase | 30 | increase | Increase |
| New investment | 20 | new investment, new invest, new inv | New investment |
| Other | 0 | (Fallback) | Other |

## Global Field Constraints
| Field Name | Constraints / Mappings |
| --- | --- |
| Securities ID (*) | Should be ISIN<br>12 characters<br>Don't include special characters |
| Securities Name (*) | Should be named clearly |
| Securities Type (*) | Fill in the ID in respective Securities Type per list on enoFin: Securities/ List/ Securities type |
| Securities Class (*) | Please fill in respective Securities Class ID per Securities Class List |
| Commission Method (*) | Mappings: {"Capitalised": "CAPITALISED", "Expense off": "EXPENSE_OFF"} |
| Ticker | Fill in ticker name, if securities don't have ticker --> fill in NA |
| Sector (*) | Please fill in respective Securities Class ID per Securities Class List |
| Currency (*) | Please fill in the Currency in SYSTEM/CURRENCIES |
| Cost Method (*) | Mappings: {"FIFO": "NTXT", "Average Cost": "BQ"} |
| Quantity (*) | Units of securities<br>Quantity >= 0 |
| Foreign Unit Price (*) | Maximum 12 decimals |
| Foreign Transaction Fee | Maximum 2 decimals |
