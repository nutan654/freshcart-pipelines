# Architecture — Break It Till It Holds

```mermaid
flowchart TD
    DEV[Developer working tree] --> GIT[Git repository]
    GIT -->|push| CI[GitHub Actions: Python 3.12 + pytest]
    CI -->|validated code / manual ELT run| EXT
    CI -->|A1 test_size fault| GATE{120 train / 30 test?}

    subgraph ELT[FreshCart Snowflake ELT]
      EXT[Extract: web / mobile / CRM / FX] --> LAND[Compressed NDJSON landing]
      LAND --> BR[(Bronze raw VARIANT)]
      BR --> S1[Silver normalize + validate]
      S1 -->|invalid reasons| Q[(Quarantine)]
      S1 --> DEDUP[Silver dedup: QUALIFY ROW_NUMBER]
      DEDUP --> ENR[Point-in-time CRM / FX / pincode joins]
      ENR --> GOLD[(Gold fact orders: row_hash + MERGE)]
      GOLD --> QC[Quality checks]
      F_B2[B2: EUR currency] -. inject .-> S1
      F_B3[B3: CRM tier event] -. inject .-> ENR
      F_B4[B4: future order] -. inject .-> QC
      DEDUP -. replay .-> GOLD
    end

    subgraph MAGE[Mage Iris ML]
      LOAD[load_iris] --> VAL[validate_input @test]
      VAL --> PREP[prepare_data @test 120 / 30]
      PREP --> TRAIN[train_model @test >= 0.80]
      TRAIN --> SAVE[save_results: predictions CSV]
      TRAIN --> EVAL[evaluate_model: confusion matrix / metrics]
      F_C2[C2: missing value / class] -. inject .-> VAL
      F_C1[C1: max_depth 1..5] -. inject .-> TRAIN
    end

    subgraph MQ[RabbitMQ event stream]
      DIS[Dispatcher] --> EX((rapido-dispatch topic exchange))
      EX --> DR[Private driver queues]
      DR --> ACK[ACK valid / NACK invalid]
      EX --> CRASH[Durable crash-demo queue]
      CRASH --> REDELIVER[Redelivery after consumer reconnect]
      F_D1[D1: missing zone] -. inject .-> ACK
      F_D2[D2: crash before ACK] -. inject .-> CRASH
    end

    BONUS[Optional order events] -.-> LAND
```

## Detection boundaries

- **A1:** `pytest` checks the instructor's 80/20 split in local CI.
- **B2:** `ARRAY_CONSTRUCT_COMPACT` builds reason codes; `silver.orders_clean` excludes rows
  with reasons and the quarantine insert stores each source version once.
- **B1:** Silver chooses one order version; Gold `MERGE` changes only when `row_hash` changes.
- **B3:** SCD2 intervals select the customer tier effective on the order date.
- **B4:** `quality_checks()` reports future-dated deduplicated orders.
- **C1/C2:** Mage `@test` functions stop downstream blocks when their output contract fails.
- **D1:** consumers NACK malformed messages with `requeue=False`; D2 demonstrates broker
  redelivery for an unacknowledged message after process death.
