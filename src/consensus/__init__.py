"""
Consensus layer - Voting and Finality
"""

from .vote import Vote, VoteCollector
from .finality import FinalityManager

__all__ = ['Vote', 'VoteCollector', 'FinalityManager']