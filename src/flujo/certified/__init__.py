"""A certified query engine: answer only what the evidence gives the right to answer.

The public surface is small on purpose.

    load_contracts()   the fourteen audited query contracts
    build_ssd_tree()   a summary tree over the portable SSD index
    build_ig_tree()    a summary tree over the Instagram export
    certify()          one contract against one summary, never opening a member
    refine()           certify, and open children only where a certificate fails
    answer()           a typed answer plus what the walk cost

Everything else is internal. The rule that governs all of it: a negative
certificate by absence is valid only when the authority is complete for the
predicate over every member, and a certificate always says whether it answered
the human question or a narrowed predicate.
"""

from .certify import Certificate, Refinement, answer, certify, refine
from .contracts import (
    CERTIFIED_NO,
    CERTIFIED_YES,
    UNKNOWN,
    ContractError,
    QueryContract,
    load_contracts,
)
from .summary import (
    CORPUS_CLAIM,
    POLICY_CLAIM,
    WORLD_CLAIM,
    Summary,
    SummaryError,
)
from .tree import TreeNode, build_ig_tree, build_ssd_tree

__all__ = [
    "Certificate", "Refinement", "answer", "certify", "refine",
    "CERTIFIED_NO", "CERTIFIED_YES", "UNKNOWN", "ContractError", "QueryContract",
    "load_contracts", "CORPUS_CLAIM", "POLICY_CLAIM", "WORLD_CLAIM", "Summary",
    "SummaryError", "TreeNode", "build_ig_tree", "build_ssd_tree",
]
