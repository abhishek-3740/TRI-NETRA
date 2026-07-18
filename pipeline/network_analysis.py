"""
pipeline/network_analysis.py
Mule Account Network Analysis for TRI-NETRA (ERH26_PS_03).

Builds a directed transaction graph from bank data and flags
pass-through (mule) accounts using degree + throughput heuristics.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import matplotlib
matplotlib.use("Agg")  # headless backend
import matplotlib.pyplot as plt
import networkx as nx
import polars as pl


# ── Config ───────────────────────────────────────────────────────────────────

TOP_N_MULES = 50
MIN_TRANSACTIONS = 3  # ignore accounts with < N total edges


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class MuleAccount:
    account: str
    bank_name: str
    risk_score: float
    in_degree: int
    out_degree: int
    money_in: float
    money_out: float
    throughput_ratio: float
    total_volume: float
    unique_senders: List[str] = field(default_factory=list)
    unique_receivers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "account": self.account,
            "bank_name": self.bank_name,
            "risk_score": round(self.risk_score, 4),
            "in_degree": self.in_degree,
            "out_degree": self.out_degree,
            "money_in": round(self.money_in, 2),
            "money_out": round(self.money_out, 2),
            "throughput_ratio": round(self.throughput_ratio, 4),
            "total_volume": round(self.total_volume, 2),
            "unique_senders": self.unique_senders,
            "unique_receivers": self.unique_receivers,
        }


# ── Graph Builder ────────────────────────────────────────────────────────────

def build_transaction_graph(df: pl.DataFrame) -> nx.DiGraph:
    """
    Build a directed graph from bank transactions.
    Nodes = accounts, Edges = sender → receiver, weight = amount.
    Only SUCCESS transactions are included.
    """
    # Filter to successful transactions
    df_ok = df.filter(pl.col("Transaction_Status") == "SUCCESS")

    # Aggregate multiple transactions between same sender→receiver pair
    agg = df_ok.group_by(
        ["Sender_Account_Number", "Receiver_Account_Number"]
    ).agg(
        pl.col("Transaction_Amount").sum().alias("total_amount"),
        pl.col("Transaction_Amount").count().alias("txn_count"),
        pl.col("Sender_Bank_Name").first().alias("sender_bank"),
        pl.col("Receiver_Bank_Name").first().alias("receiver_bank"),
    )

    G = nx.DiGraph()

    for row in agg.iter_rows(named=True):
        sender = str(row["Sender_Account_Number"])
        receiver = str(row["Receiver_Account_Number"])
        amount = float(row["total_amount"])
        count = int(row["txn_count"])

        # Add nodes with bank metadata
        if sender not in G:
            G.add_node(sender, bank=row["sender_bank"])
        if receiver not in G:
            G.add_node(receiver, bank=row["receiver_bank"])

        # Add / update edge
        if G.has_edge(sender, receiver):
            G[sender][receiver]["weight"] += amount
            G[sender][receiver]["count"] += count
        else:
            G.add_edge(sender, receiver, weight=amount, count=count)

    print(f"[NA] Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


# ── Mule Detection ───────────────────────────────────────────────────────────

def detect_mule_accounts(
    G: nx.DiGraph,
    top_n: int = TOP_N_MULES,
    min_edges: int = MIN_TRANSACTIONS,
) -> List[MuleAccount]:
    """
    Score every node on mule-like pass-through behavior:

    Heuristic:
      • High in-degree  (receives from many distinct accounts)
      • High out-degree (sends to many distinct accounts)
      • money_in ≈ money_out  (pass-through, not accumulation)
      • High total volume

    Risk Score = (in_degree × out_degree) × throughput_ratio × log1p(total_volume)
    """
    mules: List[MuleAccount] = []

    for node in G.nodes():
        in_deg = G.in_degree(node)
        out_deg = G.out_degree(node)
        total_edges = in_deg + out_deg

        if total_edges < min_edges:
            continue

        # Money in = sum of incoming edge weights
        money_in = sum(
            float(G[pred][node]["weight"]) for pred in G.predecessors(node)
        )
        # Money out = sum of outgoing edge weights
        money_out = sum(
            float(G[node][succ]["weight"]) for succ in G.successors(node)
        )

        total_volume = money_in + money_out

        # Throughput ratio: 1.0 = perfect pass-through, 0.0 = all one-way
        if max(money_in, money_out) > 0:
            throughput_ratio = min(money_in, money_out) / max(money_in, money_out)
        else:
            throughput_ratio = 0.0

        # Composite risk score
        # Multiply degree product by throughput (mules balance in/out) and volume
        degree_product = (in_deg + 1) * (out_deg + 1)  # +1 to avoid zeroing out
        risk_score = (
            degree_product
            * throughput_ratio
            * math.log1p(total_volume)
        )

        mules.append(
            MuleAccount(
                account=node,
                bank_name=G.nodes[node].get("bank", "Unknown"),
                risk_score=risk_score,
                in_degree=in_deg,
                out_degree=out_deg,
                money_in=money_in,
                money_out=money_out,
                throughput_ratio=throughput_ratio,
                total_volume=total_volume,
                unique_senders=list(G.predecessors(node)),
                unique_receivers=list(G.successors(node)),
            )
        )

    # Sort descending by risk score
    mules.sort(key=lambda m: m.risk_score, reverse=True)

    print(f"[NA] Scored {len(mules)} accounts, returning top {top_n}")
    return mules[:top_n]


# ── Visualization ──────────────────────────────────────────────────────────

def plot_mule_network(
    G: nx.DiGraph,
    mule_accounts: List[MuleAccount],
    output_path: str | Path,
    max_neighbors: int = 8,
) -> None:
    """
    Draw a subgraph containing the top mule accounts and their
    immediate neighbors (up to max_neighbors per mule).
    Saves as PNG.
    """
    if not mule_accounts:
        print("[NA] No mule accounts to plot.")
        return

    # Collect subgraph nodes: mules + limited neighbors
    sub_nodes: Set[str] = set()
    for mule in mule_accounts[:15]:  # plot top 15 mules
        sub_nodes.add(mule.account)
        preds = list(G.predecessors(mule.account))[:max_neighbors]
        succs = list(G.successors(mule.account))[:max_neighbors]
        sub_nodes.update(preds)
        sub_nodes.update(succs)

    subG = G.subgraph(sub_nodes).copy()

    # Layout
    pos = nx.spring_layout(subG, k=0.8, iterations=50, seed=42)

    # Color mapping
    mule_ids = {m.account for m in mule_accounts[:15]}
    node_colors = [
        "#ef4444" if n in mule_ids else "#3b82f6"
        for n in subG.nodes()
    ]
    node_sizes = [
        400 if n in mule_ids else 150
        for n in subG.nodes()
    ]

    # Edge weights for width
    edge_widths = [
        max(0.5, math.log1p(float(d["weight"])) / 5)
        for _, _, d in subG.edges(data=True)
    ]

    fig, ax = plt.subplots(figsize=(14, 10))
    nx.draw_networkx_nodes(
        subG, pos, node_color=node_colors, node_size=node_sizes, alpha=0.9, ax=ax
    )
    nx.draw_networkx_edges(
        subG, pos, width=edge_widths, alpha=0.4, arrows=True,
        arrowsize=10, connectionstyle="arc3,rad=0.1", ax=ax
    )
    nx.draw_networkx_labels(
        subG, pos, font_size=6, font_color="white", ax=ax
    )

    ax.set_title(
        f"TRI-NETRA Mule Network (Top {len(mule_ids)} mules + neighbors)",
        fontsize=14, color="white", pad=10
    )
    ax.axis("off")
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#0f172a")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor="#0f172a", bbox_inches="tight")
    plt.close(fig)
    print(f"[NA] Network plot saved to {output_path}")


# ── Persistence ──────────────────────────────────────────────────────────────

def save_mule_accounts(mules: List[MuleAccount], path: str | Path) -> None:
    out = {
        "generated_at": datetime.now().isoformat(),
        "count": len(mules),
        "mule_accounts": [m.to_dict() for m in mules],
    }
    Path(path).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[NA] Saved {len(mules)} mule accounts to {path}")


# ── Main Runner ──────────────────────────────────────────────────────────────

def run_network_analysis(
    bank_path: str | Path,
    out_json: str | Path,
    out_png: Optional[str | Path] = None,
    top_n: int = TOP_N_MULES,
) -> List[MuleAccount]:
    df = pl.read_csv(bank_path, try_parse_dates=True, infer_schema_length=1000000)
    print(f"[NA] Loaded {df.height} bank transactions")

    G = build_transaction_graph(df)
    mules = detect_mule_accounts(G, top_n=top_n)
    save_mule_accounts(mules, out_json)

    if out_png:
        plot_mule_network(G, mules, out_png)

    return mules


if __name__ == "__main__":
    ROOT = Path(__file__).parent.parent

    run_network_analysis(
        bank_path=ROOT / "data" / "final" / "bank_transactions.csv",
        out_json=ROOT / "data" / "final" / "mule_accounts.json",
        out_png=ROOT / "data" / "final" / "mule_network.png",
        top_n=50,
    )