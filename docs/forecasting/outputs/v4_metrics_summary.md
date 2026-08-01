### Model Evaluation on Holdout Period (2024–2025)

| Metric | Value | What it means |
| ------ | ----- | ------------- |
| MSE | 3,386,101,902.59 | Average squared error in USD²; lower is better. |
| Avg. % error (MAPE) | 6.00% | Average absolute forecast error as a share of actual revenue; easier for stakeholders than USD². |
| RMSE (from MSE) | $58,190 | Typical monthly error scale in USD (√MSE); complements MAPE. |
| PSI | 8.3685 | Target drift: training vs holdout revenue distribution (lower = more stable). |
| Gini | 0.7414 | Ranking quality of predictions vs actuals (1.0 = perfect). |
| K2 | 9.23 | D'Agostino-Pearson K² on holdout residuals; lower = more random error shape. |

Low MSE alone is not enough: PSI flags train→holdout target drift, K2 (D'Agostino) flags residual shape, Gini flags ranking quality.