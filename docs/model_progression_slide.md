# Model Progression Slide

**Story arc for judges:** Rules -> Unsupervised ML -> Graph ML

1. **Rule-based scoring** (baseline): Grooming Call, Digital Alibi, Rapid Layering, Circular Flow.
2. **Isolation Forest**: unsupervised anomaly detection over transaction features, trained on 100k synthetic records. Show ROC curve + precision/recall.
3. **Graph ML (GraphSAGE, Node2Vec fallback)**: node embeddings over the money-flow graph feed a Logistic Regression classifier, catching mule patterns no hand-written rule anticipated.

**Key line:** "We don't just show data — we show a model that gets smarter at every layer."
