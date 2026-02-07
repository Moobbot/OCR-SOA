# System Architecture & Flow

## 1. High-Level Component Architecture

This diagram shows how the components interact, from input rules to the plugin-based extraction logic.

```mermaid
graph TD
    User[User / Input] -->|Config| Rules[rule.json]
    User -->|Input Files| OCR[run_ocr.py]
    OCR -->|Markdown Outputs| MDFiles[outputs/*.md]

    subgraph Extraction System [extract_data.py]
        Runner[Main Runner]
        Registry[Plugin Registry]

        subgraph Plugins
            Pos[PositionsPlugin]
            Trade[TradeInformationPlugin]
            FX[FXTFPlugin]
            Others[OthersPlugin]
        end
    end

    Rules --> Runner
    MDFiles --> Runner
    Runner --> Registry
    Registry --> Pos
    Registry --> Trade
    Registry --> FX
    Registry --> Others

    Trade -.->|Delegation: is_fx?| FX
```

## 2. Detailed Execution Sequence (Row Classification)

This sequence diagram details how a specific transaction row is processed, showing the priority check for FX types.

```mermaid
sequenceDiagram
    participant Main as extract_data.py
    participant Trade as TradeInformationPlugin
    participant FX as FXTFPlugin

    Note over Main: Processing Page 17 (Transaction List)

    Main->>Trade: extract(text)
    activate Trade

    Trade->>FX: Instantiate FXTFPlugin(rules)

    loop For Each Row in Table
        Note right of Trade: Row: "15.07.2025 FX SPOT USD/SGD"

        Trade->>FX: is_fx_transaction("FX SPOT...")
        activate FX
        FX->>FX: Check "FX Spot", "FX Forward" rules
        FX-->>Trade: True, "FX Spot"
        deactivate FX

        alt is_fx == True
            Trade->>Trade: Assign to Section "FX & TF"
        else is_fx == False
            Trade->>Trade: Run Standard Classification
            Trade->>Trade: Assign to Section "Trade information"
        end
    end

    Trade-->>Main: Return Data (Rows mapped to Sections)
    deactivate Trade
```
