# Predictions — record these before live experiments

These are pre-run predictions derived from the assignment's supplied rules and input data.
Keep the **Actual after run** column empty until you execute the experiment and capture it.

## D1: topic routing predictions

| # | Routing key | Predicted receiving queues | Actual live queues |
|---:|---|---|---|
| 1 | `bangalore.koramangala.food` | Ravi, Meena, Control | Pending |
| 2 | `bangalore.indiranagar.ride` | Priya, Arjun, Control | Pending |
| 3 | `bangalore.whitefield.ride` | Arjun, Control | Pending |
| 4 | `chennai.tnagar.food` | Karthik | Pending |
| 5 | `chennai.whitefield.ride` | None | Pending |
| 6 | `bangalore.koramangala` | Control | Pending |

For case 6, `bangalore.#` can match the two-word key because `#` can match zero or more
words after `bangalore`. The other patterns have three components and their `*` requires
exactly one word, so they do not match a missing third component.

## B3: CUST-02 Arjun tier change to Gold, effective 2026-08-15

The supplied order `ORD-1002` is dated 2026-09-01, which is after the proposed effective
date. Its original INR amount is 42.50 USD × 83.20 = ₹3,536.00. Silver has multiplier 1;
Gold has multiplier 2; loyalty points use `FLOOR(amount_inr / 100) * multiplier`.

| Quantity | Prediction before run | Actual after run |
|---|---:|---:|
| Rows for CUST-02 in `dim.customers_scd2` | 2 | Pending |
| Tier used for ORD-1002 | Gold | Pending |
| Loyalty points for ORD-1002 | 70 | Pending |
| Total loyalty points in Gold | 161 | Pending |
| Gold rows whose `published_at` changes | 1 | Pending |

The original baseline points are 126. The Arjun tier change doubles only ORD-1002's
multiplier, so its points move from 35 to 70 (+35), predicting 161 overall. Only that
Gold row's `row_hash` should change and cause a `published_at` update. These remain
predictions until the Snowflake experiment is run.
