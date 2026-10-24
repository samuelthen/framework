"""Candidate-redundancy rate as a range across the two annotators (primary v2 vs MODEL_2), each with uncertain
counted both ways. MODEL_2 labelled every matched pilot op; only matched ops can be candidate-redundant, so the
MODEL_2 view = primary v2 labels with every MODEL_2 label substituted in. Writes results/v2/task4/annotator_range.csv."""
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import m4_pilot as P  # noqa: E402

OUT = f"{P.ROOT}/results/v2/task4"
TMP = f"{P.ROOT}/data/graphs_v2_model2view"


def main():
    prim, m2 = P.read_labels("pilot_v2"), P.read_labels("pilot_model2")
    with open(f"{P.LAB}/pilot_v2_model2view.jsonl", "w") as f:
        for k, r in {**prim, **m2}.items():
            f.write(json.dumps(r) + "\n")
    P.analyze("pilot_v2_model2view", RES=f"{OUT}/model2view", graphs=TMP)
    rows = []
    for ann, path in (("primary", f"{P.ROOT}/results/v2/task2/measures_by_model.csv"), ("model2", f"{OUT}/model2view/measures_by_model.csv")):
        M = pd.read_csv(path)
        for _, r in M.iterrows():
            rows.append({"model": r.model, "annotator": ann, "lo": r.cand_redundancy_rate_lo, "lo_ci": r.cand_redundancy_rate_lo_ci,
                         "hi": r.cand_redundancy_rate_hi, "hi_ci": r.cand_redundancy_rate_hi_ci})
    R = pd.DataFrame(rows)
    rng = R.groupby("model").agg(min_lo=("lo", "min"), max_hi=("hi", "max")).reset_index()
    R.to_csv(f"{OUT}/annotator_range.csv", index=False)
    print(R.round(4).to_string()); print(rng.round(4).to_string())


if __name__ == "__main__":
    main()
