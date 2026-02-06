# Rule Analysis & Mapping

This document transforms the raw rules from `some_rule.txt` into structured tables for verification.
**Global Constraints** have been merged into the specific columns where applicable.

## 1. Trade Information

**Page Identification**: Header keyword is `Transaction list`

| Index | Column Name                 | Format | Rules / Constraints / Mapping                                                                                                                                                                                                               |
| :---- | :-------------------------- | :----- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1     | Client name                 | Text   |                                                                                                                                                                                                                                             |
| 2     | Name/ Security              | Text   | **Securities Name (\*)**: Should be named clearly                                                                                                                                                                                           |
| 3     | Securities ID               | Text   | **Extraction**: ISIN (12 characters)<br>**Constraint**: Should be ISIN, Max 15 chars, No special chars                                                                                                                                      |
| 4     | Transaction type            | Text   | **Mapping**: <br>`We have SOLD to you as PRINCIPAL` -> Buy/Purchase<br>`We have SOLD for you as AGENT` -> Sell/Sale<br>`We have BROUGHT for you as AGENT` -> Buy/Purchase<br>`Sec. receipt` -> Buy/Purchase<br>`Sec. delivery` -> Sale/Sell |
| 5     | Trade date                  | Date   | **Keywords**: `trade date`, `traded on`, `booking date...`                                                                                                                                                                                  |
| 6     | Settlement date             | Number | **Keywords**: `Value date`, `Settlement due on`, `Settlement date`, `payment date`, `Receipt date`                                                                                                                                          |
| 7     | Quantity                    | Text   | **Constraint**: Units of securities, Quantity >= 0                                                                                                                                                                                          |
| 8     | Foreign Unit Price          | Number | **Constraint**: Max 12 decimals                                                                                                                                                                                                             |
| 9     | Foreign Gross consideration | Text   | **Rule**: Take absolute value                                                                                                                                                                                                               |
| 10    | Foreign Transaction Fee     | Number | **Keywords**: `Commision`, `Exce commission`, `research commission`, `Local fee`, `local tax`, `stamp duty`<br>**Constraint**: Max 2 decimals                                                                                               |
| 11    | Accrued interest            | Text   |                                                                                                                                                                                                                                             |
| 12    | Foreign Net consideration   | Number |                                                                                                                                                                                                                                             |
| 13    | Currency                    | Text   | **Constraint**: Map to `SYSTEM/CURRENCIES`                                                                                                                                                                                                  |
| 14    | Net consideration           | Number |                                                                                                                                                                                                                                             |
| 15    | Account no.                 | Text   |                                                                                                                                                                                                                                             |
| 16    | Commission fee (Base)       | Number |                                                                                                                                                                                                                                             |

---

## 2. FX & TF

**Page Identification**: Header keyword is `Transaction list`

| Index | Column Name      | Format | Rules / Constraints / Mapping                                                                                          |
| :---- | :--------------- | :----- | :--------------------------------------------------------------------------------------------------------------------- |
| 1     | Client name      | Text   |                                                                                                                        |
| 2     | Transaction type | Text   |                                                                                                                        |
| 3     | Trade date       | Date   |                                                                                                                        |
| 4     | Settlement date  | Number |                                                                                                                        |
| 5     | Rate             | Number |                                                                                                                        |
| 6     | Currency Buy     | Text   | **Constraint**: Map to `SYSTEM/CURRENCIES`                                                                             |
| 7     | Amount Buy       | Number |                                                                                                                        |
| 8     | Currency Sell    | Text   | **Constraint**: Map to `SYSTEM/CURRENCIES`                                                                             |
| 9     | Amount Sell      | Number |                                                                                                                        |
| 10    | Account no. Buy  | Text   | **Logic**: If line "You bought [Curr]..." matches `Currency Buy`, this is the account.<br>(See detailed logic in text) |
| 11    | Account no. Sell | Text   | **Logic**: If line "You sold [Curr]..." matches `Currency Sell`, this is the account.<br>(See detailed logic in text)  |

---

## 3. Others

| Index | Column Name                       | Format | Rules / Constraints / Mapping                                  |
| :---- | :-------------------------------- | :----- | :------------------------------------------------------------- |
| 1     | Client name                       | Text   |                                                                |
| 2     | Description                       | Text   |                                                                |
| 3     | Securities ID/ Ref-No.            | Text   | **Constraint**: Should be ISIN, Max 15 chars, No special chars |
| 4     | Transaction type                  | Date   |                                                                |
| 5     | Trade date                        | Text   |                                                                |
| 6     | Settlement date                   | Number |                                                                |
| 7     | Currency                          | Text   | **Constraint**: Map to `SYSTEM/CURRENCIES`                     |
| 8     | Quantity                          | Text   | **Constraint**: Units of securities, Quantity >= 0             |
| 9     | Foreign Unit Price/ Interest rate | Number | **Constraint**: Max 12 decimals                                |
| 10    | Foreign Gross Amount/Interest     | Text   |                                                                |
| 11    | Tax rate (%)                      | Text   |                                                                |
| 12    | Tax amount                        | Number |                                                                |
| 13    | Foreign Net Amount                | Number |                                                                |
| 14    | Payment mode                      | Text   |                                                                |
| 15    | Account no.                       | Text   |                                                                |
| 16    | Exrate to GST                     | Number |                                                                |
| 17    | Amount (SGD)                      | Number |                                                                |

---

## 4. Positions

**Page Identification**: Header keyword is `Detailed positions`

| Index | Column Name      | Format | Rules / Constraints / Mapping                                                                                                    |
| :---- | :--------------- | :----- | :------------------------------------------------------------------------------------------------------------------------------- |
| 1     | Portfolio No.    | Text   |                                                                                                                                  |
| 2     | Type             | Text   | **Rule**: Extract from section headers                                                                                           |
| 3     | Account No       | Text   |                                                                                                                                  |
| 4     | Currency         | Number | **Constraint**: Map to `SYSTEM/CURRENCIES`                                                                                       |
| 5     | Quantity/ Amount | Text   | **Constraint**: Units of securities, Quantity >= 0                                                                               |
| 6     | ISIN             | Number | **Rule**: Extract from `instrument ID`, 12 chars after "ISIN:"<br>**Constraint**: Should be ISIN, Max 15 chars, No special chars |
| 7     | Secuitity name   | Text   | **Constraint**: Should be named clearly                                                                                          |
| 8     | Cost price       | Number |                                                                                                                                  |
| 9     | Market price     | Number |                                                                                                                                  |
| 10    | Market value     | Number | **Rule**: Extract from column `Market value`                                                                                     |
| 11    | Accrued interest | Number | **Rule**: Extract from column `Accrued interest`                                                                                 |
| 12    | Valuation date   | Date   | **Rule**: Extract from `“Market price on”`                                                                                       |
