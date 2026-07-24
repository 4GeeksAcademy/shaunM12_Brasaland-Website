### Model Evaluation on Holdout Period (2024–2025)

| Metric | Value | What it means |
| ------ | ----- | ------------- |
| MSE | 3,386,101,902.59 | Average squared error in USD²; lower is better. |
| PSI | 4.4767 | Distribution drift between actual and predicted revenue. |
| Gini | 0.7414 | Ranking quality of predictions vs actuals (1.0 = perfect). |
| K2 | 15,999,999.66 | Chi-square on binned distributions; closer to 0 is better. |

Low MSE alone does not guarantee a good model; PSI, Gini, and K2 catch drift, ranking, and range-level bias.