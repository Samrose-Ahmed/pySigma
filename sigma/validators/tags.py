from dataclasses import dataclass
from typing import ClassVar, List, Set
from sigma.rule import SigmaRule, SigmaRuleTag
from sigma.validators.base import SigmaRuleValidator, SigmaTagValidator, SigmaValidationIssue, SigmaValidationIssueSeverity
from sigma.data.mitre_attack import mitre_attack_tactics, mitre_attack_techniques

@dataclass
class InvalidATTACKTagIssue(SigmaValidationIssue):
    description: ClassVar[str] = "Invalid MITRE ATT&CK tagging"
    severity: ClassVar[SigmaValidationIssueSeverity] = SigmaValidationIssueSeverity.MEDIUM
    tag: SigmaRuleTag

class ATTACKTagValidator(SigmaTagValidator):
    def __init__(self) -> None:
        self.allowed_tags = {
            tactic.lower().replace("-", "_")
            for tactic in mitre_attack_tactics.values()
        }.union({
            technique.lower()
            for technique in mitre_attack_techniques.keys()
        })

    def validate_tag(self, tag: SigmaRuleTag) -> List[SigmaValidationIssue]:
        if tag.namespace == "attack" and tag.name not in self.allowed_tags:
            return [ InvalidATTACKTagIssue([ self.rule ], tag) ]
        return []

@dataclass
class InvalidTLPTagIssue(SigmaValidationIssue):
    description: ClassVar[str] = "Invalid TLP tagging"
    severity: ClassVar[SigmaValidationIssueSeverity] = SigmaValidationIssueSeverity.MEDIUM
    tag: SigmaRuleTag

class TLPTagValidatorBase(SigmaTagValidator):
    """Base class for TLP tag validation"""
    def validate_tag(self, tag: SigmaRuleTag) -> List[SigmaValidationIssue]:
        if tag.namespace == "tlp" and tag.name not in self.allowed_tags:
            return [ InvalidTLPTagIssue([ self.rule ], tag) ]
        return []

class TLPv1TagValidator(TLPTagValidatorBase):
    """Validation of TLP tags according to old version 1 standard."""
    allowed_tags: Set[str] = {
        "white",
        "green",
        "amber",
        "red",
    }

class TLPv2TagValidator(TLPTagValidatorBase):
    """Validation of TLP tags according to version 2 standard."""
    allowed_tags: Set[str] = {
        "clear",
        "green",
        "amber",
        "amber+strict",
        "red",
    }

class TLPTagValidator(TLPTagValidatorBase):
    """Validation of TLP tags from all versions of the TLP standard."""
    allowed_tags: Set[str] = TLPv1TagValidator.allowed_tags.union(TLPv2TagValidator.allowed_tags)